/*
 * wl_sqlite_jni.so -- the SQLite JNI layer this substrate never shipped.
 *
 * liboh_android_runtime.so exports 39 register_android_* JNI registrars.  Four of
 * them are 8-byte no-op stubs (`mov w0, wzr; ret`), and they are exactly the
 * database ones: SQLiteConnection, SQLiteGlobal, SQLiteDebug and CursorWindow.
 * So android.database.sqlite has no native implementation at all: every
 * SQLiteConnection.nativeOpen ends in UnsatisfiedLinkError, which is what kills
 * Noice ~3 s into MainActivity (Hilt -> PresetRepository -> Room -> getWritableDatabase).
 * It also explains the long-standing "fix104 calls the registrar, it returns 0, and
 * nothing gets bound" puzzle -- returning 0 is all those stubs do.
 *
 * This library re-implements those four registrars on top of a private copy of the
 * SQLite amalgamation and is injected with LD_PRELOAD into appspawn-x.  libart's
 * fix104 already calls every registrar by name at runtime init, and the preloaded
 * definitions win symbol resolution over the stubs, so the natives get bound in the
 * daemon and every forked app inherits them -- no libart rebuild needed.  (Verified:
 * a probe build of these four symbols is called with a live JNIEnv.)
 *
 * Deliberately out of scope, because nothing in this app path reaches them; each
 * throws rather than silently returning something wrong:
 *   - CursorWindow.nativeCreateFromParcel / nativeWriteToParcel.  Real Android backs
 *     a CursorWindow with ashmem so it can be handed to another process.  Here the
 *     window is plain heap memory, which is fine for an in-process cursor and cannot
 *     be marshalled.
 *   - SQLiteConnection.nativeExecuteForBlobFileDescriptor (ashmem again).
 *   - nativeRegisterCustomScalarFunction / nativeRegisterCustomAggregateFunction.
 *
 * The 50 native signatures registered below were read out of this board's own
 * /system/android/framework/framework.jar, not copied from an AOSP branch --
 * RegisterNatives fails silently-ish on a mismatch and the version matters
 * (e.g. nativeExecute is (JJZ)V here, it was (JJ)V before API 33).
 */

#include <jni.h>
#include <sqlite3.h>

#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <ucontext.h>
#include <unistd.h>

#include <memory>
#include <string>
#include <vector>

// stderr is not a reliable sink here: appspawn-x re-points a child's stderr partway
// through startup, so anything logged during runtime init lands in neither the daemon's
// log nor adapter_child_<pid>.stderr and simply vanishes.  Mirror to our own file, and
// stamp the pid so it is obvious which process a line came from -- daemon or app child.
void WlLog(const char* fmt, ...) __attribute__((format(printf, 1, 2)));

void WlLog(const char* fmt, ...) {
  static FILE* sink = nullptr;
  if (sink == nullptr) sink = fopen("/data/local/tmp/wl_shim.log", "a");
  char buf[1024];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  fprintf(stderr, "[wl_sqlite pid=%d] %s", getpid(), buf);
  fflush(stderr);
  if (sink != nullptr) {
    fprintf(sink, "[pid=%d] %s", getpid(), buf);
    fflush(sink);
  }
}

#define WL_LOG(...) WlLog(__VA_ARGS__)

namespace {

// ---------------------------------------------------------------- exceptions

void ThrowJava(JNIEnv* env, const char* cls, const char* msg) {
  jclass c = env->FindClass(cls);
  if (c != nullptr) {
    env->ThrowNew(c, msg);
    env->DeleteLocalRef(c);
    return;
  }
  env->ExceptionClear();
  jclass re = env->FindClass("java/lang/RuntimeException");
  if (re != nullptr) {
    env->ThrowNew(re, msg);
    env->DeleteLocalRef(re);
  }
}

// Mirrors AOSP's throw_sqlite3_exception: the Java layer keys real behaviour off the
// exception *class* (Room retries on SQLiteDatabaseLockedException, surfaces
// constraint violations, ...), so mapping the code to the right subclass matters.
void ThrowSqlite(JNIEnv* env, sqlite3* db, int code, const char* extra) {
  const char* msg = (db != nullptr) ? sqlite3_errmsg(db) : sqlite3_errstr(code);
  if (code == SQLITE_OK && db != nullptr) code = sqlite3_extended_errcode(db);
  char buf[512];
  snprintf(buf, sizeof(buf), "%s (code %d)%s%s", (msg != nullptr) ? msg : "unknown error",
           code, (extra != nullptr) ? ": " : "", (extra != nullptr) ? extra : "");

  const char* cls = "android/database/sqlite/SQLiteException";
  switch (code & 0xff) {
    case SQLITE_CONSTRAINT: cls = "android/database/sqlite/SQLiteConstraintException"; break;
    case SQLITE_ABORT:      cls = "android/database/sqlite/SQLiteAbortException"; break;
    case SQLITE_DONE:       cls = "android/database/sqlite/SQLiteDoneException"; break;
    case SQLITE_FULL:       cls = "android/database/sqlite/SQLiteFullException"; break;
    case SQLITE_MISUSE:     cls = "android/database/sqlite/SQLiteMisuseException"; break;
    case SQLITE_PERM:
    case SQLITE_AUTH:       cls = "android/database/sqlite/SQLiteAccessPermException"; break;
    case SQLITE_BUSY:       cls = "android/database/sqlite/SQLiteDatabaseLockedException"; break;
    case SQLITE_LOCKED:     cls = "android/database/sqlite/SQLiteTableLockedException"; break;
    case SQLITE_READONLY:   cls = "android/database/sqlite/SQLiteReadOnlyDatabaseException"; break;
    case SQLITE_CANTOPEN:   cls = "android/database/sqlite/SQLiteCantOpenDatabaseException"; break;
    case SQLITE_CORRUPT:
    case SQLITE_NOTADB:     cls = "android/database/sqlite/SQLiteDatabaseCorruptException"; break;
    case SQLITE_IOERR:      cls = "android/database/sqlite/SQLiteDiskIOException"; break;
    case SQLITE_NOMEM:      cls = "java/lang/OutOfMemoryError"; break;
    case SQLITE_INTERRUPT:  cls = "android/os/OperationCanceledException"; break;
    default: break;
  }
  ThrowJava(env, cls, buf);
}

// ---------------------------------------------------------------- connection

struct Connection {
  sqlite3* db = nullptr;
  std::string label;
  bool cancelled = false;
};

Connection* Conn(jlong p) { return reinterpret_cast<Connection*>(p); }
sqlite3_stmt* Stmt(jlong p) { return reinterpret_cast<sqlite3_stmt*>(p); }

// Android schemas may say COLLATE LOCALIZED / UNICODE.  Real Android backs those with
// ICU; a codepoint comparison keeps such statements from failing to prepare, which is
// all this app needs.  Ordering of non-ASCII text will differ from a real device.
int CollateCodepoint(void*, int lenA, const void* a, int lenB, const void* b) {
  const jchar* pa = static_cast<const jchar*>(a);
  const jchar* pb = static_cast<const jchar*>(b);
  int na = lenA / 2, nb = lenB / 2, n = (na < nb) ? na : nb;
  for (int i = 0; i < n; i++) {
    if (pa[i] != pb[i]) return (pa[i] < pb[i]) ? -1 : 1;
  }
  if (na == nb) return 0;
  return (na < nb) ? -1 : 1;
}

void RegisterCollators(sqlite3* db) {
  sqlite3_create_collation_v2(db, "localized", SQLITE_UTF16, nullptr, CollateCodepoint, nullptr);
  sqlite3_create_collation_v2(db, "LOCALIZED", SQLITE_UTF16, nullptr, CollateCodepoint, nullptr);
  sqlite3_create_collation_v2(db, "unicode", SQLITE_UTF16, nullptr, CollateCodepoint, nullptr);
  sqlite3_create_collation_v2(db, "UNICODE", SQLITE_UTF16, nullptr, CollateCodepoint, nullptr);
}

jlong nativeOpen(JNIEnv* env, jclass, jstring pathStr, jint openFlags, jstring labelStr,
                 jboolean, jboolean, jint lookasideSz, jint lookasideCnt) {
  const char* path = env->GetStringUTFChars(pathStr, nullptr);
  if (path == nullptr) return 0;

  // SQLiteDatabase's flag bits, same values as AOSP: OPEN_READWRITE 0, OPEN_READONLY 1,
  // CREATE_IF_NECESSARY 0x10000000.
  int flags;
  if (openFlags & 0x10000000) {
    flags = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE;
  } else if (openFlags & 1) {
    flags = SQLITE_OPEN_READONLY;
  } else {
    flags = SQLITE_OPEN_READWRITE;
  }

  sqlite3* db = nullptr;
  int rc = sqlite3_open_v2(path, &db, flags, nullptr);
  if (rc != SQLITE_OK) {
    char buf[512];
    snprintf(buf, sizeof(buf), "Could not open database '%s' (code %d)", path, rc);
    WL_LOG("open FAILED %s rc=%d\n", path, rc);
    env->ReleaseStringUTFChars(pathStr, path);
    if (db != nullptr) sqlite3_close_v2(db);
    ThrowJava(env, "android/database/sqlite/SQLiteCantOpenDatabaseException", buf);
    return 0;
  }

  if (lookasideSz >= 0 && lookasideCnt >= 0) {
    sqlite3_db_config(db, SQLITE_DBCONFIG_LOOKASIDE, nullptr, lookasideSz, lookasideCnt);
  }
  sqlite3_busy_timeout(db, 2500);  // AOSP's BUSY_TIMEOUT_MS
  RegisterCollators(db);

  Connection* c = new Connection();
  c->db = db;
  if (labelStr != nullptr) {
    const char* label = env->GetStringUTFChars(labelStr, nullptr);
    if (label != nullptr) {
      c->label = label;
      env->ReleaseStringUTFChars(labelStr, label);
    }
  }
  WL_LOG("open ok %s\n", path);
  env->ReleaseStringUTFChars(pathStr, path);
  return reinterpret_cast<jlong>(c);
}

void nativeClose(JNIEnv*, jclass, jlong connPtr) {
  Connection* c = Conn(connPtr);
  if (c == nullptr) return;
  if (c->db != nullptr) sqlite3_close_v2(c->db);
  delete c;
}

void nativeRegisterCustomScalarFunction(JNIEnv* env, jclass, jlong, jstring, jobject) {
  ThrowJava(env, "java/lang/UnsupportedOperationException",
            "custom scalar functions are not implemented by wl_sqlite_jni");
}

void nativeRegisterCustomAggregateFunction(JNIEnv* env, jclass, jlong, jstring, jobject) {
  ThrowJava(env, "java/lang/UnsupportedOperationException",
            "custom aggregate functions are not implemented by wl_sqlite_jni");
}

void nativeRegisterLocalizedCollators(JNIEnv*, jclass, jlong connPtr, jstring) {
  Connection* c = Conn(connPtr);
  if (c != nullptr) RegisterCollators(c->db);
}

jlong nativePrepareStatement(JNIEnv* env, jclass, jlong connPtr, jstring sqlStr) {
  Connection* c = Conn(connPtr);
  const jchar* sql = env->GetStringChars(sqlStr, nullptr);
  jsize len = env->GetStringLength(sqlStr);
  sqlite3_stmt* st = nullptr;
  int rc = sqlite3_prepare16_v2(c->db, sql, len * sizeof(jchar), &st, nullptr);
  env->ReleaseStringChars(sqlStr, sql);
  if (rc != SQLITE_OK) {
    ThrowSqlite(env, c->db, rc, "while compiling statement");
    return 0;
  }
  return reinterpret_cast<jlong>(st);
}

void nativeFinalizeStatement(JNIEnv*, jclass, jlong, jlong stmtPtr) {
  sqlite3_finalize(Stmt(stmtPtr));
}

jint nativeGetParameterCount(JNIEnv*, jclass, jlong, jlong stmtPtr) {
  return sqlite3_bind_parameter_count(Stmt(stmtPtr));
}

jboolean nativeIsReadOnly(JNIEnv*, jclass, jlong, jlong stmtPtr) {
  return sqlite3_stmt_readonly(Stmt(stmtPtr)) ? JNI_TRUE : JNI_FALSE;
}

jint nativeGetColumnCount(JNIEnv*, jclass, jlong, jlong stmtPtr) {
  return sqlite3_column_count(Stmt(stmtPtr));
}

jstring nativeGetColumnName(JNIEnv* env, jclass, jlong, jlong stmtPtr, jint index) {
  const void* name = sqlite3_column_name16(Stmt(stmtPtr), index);
  if (name == nullptr) return nullptr;
  const jchar* p = static_cast<const jchar*>(name);
  jsize n = 0;
  while (p[n] != 0) n++;
  return env->NewString(p, n);
}

void nativeBindNull(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jint index) {
  int rc = sqlite3_bind_null(Stmt(stmtPtr), index);
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

void nativeBindLong(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jint index, jlong value) {
  int rc = sqlite3_bind_int64(Stmt(stmtPtr), index, value);
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

void nativeBindDouble(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jint index, jdouble value) {
  int rc = sqlite3_bind_double(Stmt(stmtPtr), index, value);
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

void nativeBindString(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jint index, jstring value) {
  const jchar* s = env->GetStringChars(value, nullptr);
  jsize len = env->GetStringLength(value);
  int rc = sqlite3_bind_text16(Stmt(stmtPtr), index, s, len * sizeof(jchar), SQLITE_TRANSIENT);
  env->ReleaseStringChars(value, s);
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

void nativeBindBlob(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jint index, jbyteArray value) {
  jsize len = env->GetArrayLength(value);
  jbyte* p = env->GetByteArrayElements(value, nullptr);
  int rc = sqlite3_bind_blob(Stmt(stmtPtr), index, p, len, SQLITE_TRANSIENT);
  env->ReleaseByteArrayElements(value, p, JNI_ABORT);
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

void nativeResetStatementAndClearBindings(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr) {
  int rc = sqlite3_reset(Stmt(stmtPtr));
  if (rc == SQLITE_OK) rc = sqlite3_clear_bindings(Stmt(stmtPtr));
  if (rc != SQLITE_OK) ThrowSqlite(env, Conn(connPtr)->db, rc, nullptr);
}

// Runs the statement to completion.  Returns the sqlite code; on error the Java
// exception is already pending.
int StepDone(JNIEnv* env, Connection* c, sqlite3_stmt* st) {
  int rc = sqlite3_step(st);
  while (rc == SQLITE_ROW) rc = sqlite3_step(st);
  if (rc != SQLITE_DONE && rc != SQLITE_OK) {
    ThrowSqlite(env, c->db, rc, nullptr);
  }
  return rc;
}

void nativeExecute(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr, jboolean /*isPragmaStmt*/) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  StepDone(env, c, st);
  sqlite3_reset(st);
}

jlong nativeExecuteForLong(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  jlong out = -1;
  int rc = sqlite3_step(st);
  if (rc == SQLITE_ROW && sqlite3_column_count(st) >= 1) {
    out = sqlite3_column_int64(st, 0);
    while (rc == SQLITE_ROW) rc = sqlite3_step(st);
  }
  if (rc != SQLITE_DONE && rc != SQLITE_ROW && rc != SQLITE_OK) ThrowSqlite(env, c->db, rc, nullptr);
  sqlite3_reset(st);
  return out;
}

jstring nativeExecuteForString(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  jstring out = nullptr;
  int rc = sqlite3_step(st);
  if (rc == SQLITE_ROW && sqlite3_column_count(st) >= 1) {
    const void* text = sqlite3_column_text16(st, 0);
    if (text != nullptr) {
      int bytes = sqlite3_column_bytes16(st, 0);
      out = env->NewString(static_cast<const jchar*>(text), bytes / sizeof(jchar));
    }
    while (rc == SQLITE_ROW) rc = sqlite3_step(st);
  }
  if (rc != SQLITE_DONE && rc != SQLITE_ROW && rc != SQLITE_OK) ThrowSqlite(env, c->db, rc, nullptr);
  sqlite3_reset(st);
  return out;
}

jint nativeExecuteForBlobFileDescriptor(JNIEnv* env, jclass, jlong, jlong) {
  ThrowJava(env, "java/lang/UnsupportedOperationException",
            "blob file descriptors need ashmem; not implemented by wl_sqlite_jni");
  return -1;
}

jint nativeExecuteForChangedRowCount(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  int rc = StepDone(env, c, st);
  jint changed = (rc == SQLITE_DONE) ? sqlite3_changes(c->db) : -1;
  sqlite3_reset(st);
  return changed;
}

jlong nativeExecuteForLastInsertedRowId(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  int rc = StepDone(env, c, st);
  jlong id = -1;
  if (rc == SQLITE_DONE && sqlite3_changes(c->db) > 0) id = sqlite3_last_insert_rowid(c->db);
  sqlite3_reset(st);
  return id;
}

jint nativeGetDbLookaside(JNIEnv*, jclass, jlong connPtr) {
  int cur = 0, hi = 0;
  sqlite3_db_status(Conn(connPtr)->db, SQLITE_DBSTATUS_LOOKASIDE_USED, &cur, &hi, 0);
  return cur;
}

void nativeCancel(JNIEnv*, jclass, jlong connPtr) {
  Connection* c = Conn(connPtr);
  if (c == nullptr) return;
  c->cancelled = true;
  sqlite3_interrupt(c->db);
}

void nativeResetCancel(JNIEnv*, jclass, jlong connPtr, jboolean) {
  Connection* c = Conn(connPtr);
  if (c != nullptr) c->cancelled = false;
}

// -------------------------------------------------------------- cursor window

// Field type constants from android.database.Cursor.
enum { FIELD_NULL = 0, FIELD_INTEGER = 1, FIELD_FLOAT = 2, FIELD_STRING = 3, FIELD_BLOB = 4 };

struct Cell {
  int type = FIELD_NULL;
  jlong l = 0;
  double d = 0;
  std::string s;                 // UTF-8 for strings
  std::vector<uint8_t> blob;
};

// Plain heap window.  Real Android puts this in ashmem so a Binder call can hand it to
// another process; see the header comment for why that is out of scope here.
struct Window {
  std::string name;
  size_t maxSize = 0;
  int numColumns = 0;
  std::vector<std::vector<Cell>> rows;
  size_t bytes = 0;
};

Window* Win(jlong p) { return reinterpret_cast<Window*>(p); }

Cell* CellAt(Window* w, jint row, jint col) {
  if (w == nullptr || row < 0 || col < 0) return nullptr;
  if (static_cast<size_t>(row) >= w->rows.size()) return nullptr;
  if (static_cast<size_t>(col) >= w->rows[row].size()) return nullptr;
  return &w->rows[row][col];
}

jlong cwCreate(JNIEnv* env, jclass, jstring nameStr, jint cursorWindowSize) {
  Window* w = new Window();
  w->maxSize = (cursorWindowSize > 0) ? static_cast<size_t>(cursorWindowSize) : (2u << 20);
  if (nameStr != nullptr) {
    const char* n = env->GetStringUTFChars(nameStr, nullptr);
    if (n != nullptr) {
      w->name = n;
      env->ReleaseStringUTFChars(nameStr, n);
    }
  }
  return reinterpret_cast<jlong>(w);
}

jlong cwCreateFromParcel(JNIEnv* env, jclass, jobject) {
  ThrowJava(env, "java/lang/UnsupportedOperationException",
            "CursorWindow parcelling needs ashmem; not implemented by wl_sqlite_jni");
  return 0;
}

void cwWriteToParcel(JNIEnv* env, jclass, jlong, jobject) {
  ThrowJava(env, "java/lang/UnsupportedOperationException",
            "CursorWindow parcelling needs ashmem; not implemented by wl_sqlite_jni");
}

void cwDispose(JNIEnv*, jclass, jlong p) { delete Win(p); }

jstring cwGetName(JNIEnv* env, jclass, jlong p) {
  Window* w = Win(p);
  return env->NewStringUTF((w != nullptr) ? w->name.c_str() : "");
}

void cwClear(JNIEnv*, jclass, jlong p) {
  Window* w = Win(p);
  if (w == nullptr) return;
  w->rows.clear();
  w->numColumns = 0;
  w->bytes = 0;
}

jint cwGetNumRows(JNIEnv*, jclass, jlong p) {
  Window* w = Win(p);
  return (w != nullptr) ? static_cast<jint>(w->rows.size()) : 0;
}

jboolean cwSetNumColumns(JNIEnv*, jclass, jlong p, jint columns) {
  Window* w = Win(p);
  if (w == nullptr) return JNI_FALSE;
  if (!w->rows.empty()) return JNI_FALSE;  // AOSP refuses once rows exist
  w->numColumns = columns;
  return JNI_TRUE;
}

jboolean cwAllocRow(JNIEnv*, jclass, jlong p) {
  Window* w = Win(p);
  if (w == nullptr) return JNI_FALSE;
  w->rows.emplace_back(w->numColumns);
  return JNI_TRUE;
}

void cwFreeLastRow(JNIEnv*, jclass, jlong p) {
  Window* w = Win(p);
  if (w != nullptr && !w->rows.empty()) w->rows.pop_back();
}

jint cwGetType(JNIEnv*, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  return (c != nullptr) ? c->type : FIELD_NULL;
}

jbyteArray cwGetBlob(JNIEnv* env, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr || c->type == FIELD_NULL) return nullptr;
  const uint8_t* data;
  jsize len;
  if (c->type == FIELD_BLOB) {
    data = c->blob.data();
    len = static_cast<jsize>(c->blob.size());
  } else if (c->type == FIELD_STRING) {
    data = reinterpret_cast<const uint8_t*>(c->s.data());
    len = static_cast<jsize>(c->s.size());
  } else {
    ThrowJava(env, "android/database/sqlite/SQLiteException", "unable to convert cell to blob");
    return nullptr;
  }
  jbyteArray arr = env->NewByteArray(len);
  if (arr == nullptr) return nullptr;
  env->SetByteArrayRegion(arr, 0, len, reinterpret_cast<const jbyte*>(data));
  return arr;
}

jstring cwGetString(JNIEnv* env, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return nullptr;
  char buf[64];
  switch (c->type) {
    case FIELD_STRING:  return env->NewStringUTF(c->s.c_str());
    case FIELD_INTEGER: snprintf(buf, sizeof(buf), "%lld", static_cast<long long>(c->l));
                        return env->NewStringUTF(buf);
    case FIELD_FLOAT:   snprintf(buf, sizeof(buf), "%g", c->d);
                        return env->NewStringUTF(buf);
    case FIELD_NULL:    return nullptr;
    default:
      ThrowJava(env, "android/database/sqlite/SQLiteException", "unable to convert cell to string");
      return nullptr;
  }
}

jlong cwGetLong(JNIEnv*, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return 0;
  switch (c->type) {
    case FIELD_INTEGER: return c->l;
    case FIELD_FLOAT:   return static_cast<jlong>(c->d);
    case FIELD_STRING:  return static_cast<jlong>(strtoll(c->s.c_str(), nullptr, 10));
    default:            return 0;
  }
}

jdouble cwGetDouble(JNIEnv*, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return 0;
  switch (c->type) {
    case FIELD_INTEGER: return static_cast<jdouble>(c->l);
    case FIELD_FLOAT:   return c->d;
    case FIELD_STRING:  return strtod(c->s.c_str(), nullptr);
    default:            return 0;
  }
}

void cwCopyStringToBuffer(JNIEnv* env, jclass, jlong p, jint row, jint col, jobject bufferObj) {
  jstring s = cwGetString(env, nullptr, p, row, col);
  jclass cls = env->GetObjectClass(bufferObj);
  jfieldID dataField = env->GetFieldID(cls, "data", "[C");
  jfieldID sizeField = env->GetFieldID(cls, "sizeCopied", "I");
  if (dataField == nullptr || sizeField == nullptr) {
    env->ExceptionClear();
    return;
  }
  if (s == nullptr) {
    env->SetIntField(bufferObj, sizeField, 0);
    return;
  }
  jsize len = env->GetStringLength(s);
  jcharArray data = static_cast<jcharArray>(env->GetObjectField(bufferObj, dataField));
  if (data == nullptr || env->GetArrayLength(data) < len) {
    data = env->NewCharArray(len);
    if (data == nullptr) return;
    env->SetObjectField(bufferObj, dataField, data);
  }
  const jchar* chars = env->GetStringChars(s, nullptr);
  env->SetCharArrayRegion(data, 0, len, chars);
  env->ReleaseStringChars(s, chars);
  env->SetIntField(bufferObj, sizeField, len);
}

jboolean cwPutBlob(JNIEnv* env, jclass, jlong p, jbyteArray value, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return JNI_FALSE;
  jsize len = env->GetArrayLength(value);
  c->type = FIELD_BLOB;
  c->blob.resize(len);
  env->GetByteArrayRegion(value, 0, len, reinterpret_cast<jbyte*>(c->blob.data()));
  return JNI_TRUE;
}

jboolean cwPutString(JNIEnv* env, jclass, jlong p, jstring value, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return JNI_FALSE;
  const char* s = env->GetStringUTFChars(value, nullptr);
  if (s == nullptr) return JNI_FALSE;
  c->type = FIELD_STRING;
  c->s = s;
  env->ReleaseStringUTFChars(value, s);
  return JNI_TRUE;
}

jboolean cwPutLong(JNIEnv*, jclass, jlong p, jlong value, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return JNI_FALSE;
  c->type = FIELD_INTEGER;
  c->l = value;
  return JNI_TRUE;
}

jboolean cwPutDouble(JNIEnv*, jclass, jlong p, jdouble value, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return JNI_FALSE;
  c->type = FIELD_FLOAT;
  c->d = value;
  return JNI_TRUE;
}

jboolean cwPutNull(JNIEnv*, jclass, jlong p, jint row, jint col) {
  Cell* c = CellAt(Win(p), row, col);
  if (c == nullptr) return JNI_FALSE;
  c->type = FIELD_NULL;
  return JNI_TRUE;
}

// Fills `window` from `stmt`, mirroring AOSP's packed return value:
// high 32 bits = start position, low 32 bits = total row count.
jlong nativeExecuteForCursorWindow(JNIEnv* env, jclass, jlong connPtr, jlong stmtPtr,
                                   jlong windowPtr, jint startPos, jint requiredPos,
                                   jboolean countAllRows) {
  Connection* c = Conn(connPtr);
  sqlite3_stmt* st = Stmt(stmtPtr);
  Window* w = Win(windowPtr);
  if (c == nullptr || st == nullptr || w == nullptr) {
    ThrowJava(env, "android/database/sqlite/SQLiteException", "null connection/statement/window");
    return 0;
  }

  w->rows.clear();
  w->bytes = 0;
  const int numColumns = sqlite3_column_count(st);
  w->numColumns = numColumns;

  int totalRows = 0;
  int rowIndex = 0;
  bool stoppedEarly = false;
  int rc;
  while ((rc = sqlite3_step(st)) == SQLITE_ROW) {
    totalRows++;
    if (rowIndex++ < startPos) continue;
    if (stoppedEarly) continue;  // only still stepping to finish the count

    std::vector<Cell> row(numColumns);
    size_t rowBytes = 0;
    for (int i = 0; i < numColumns; i++) {
      Cell& cell = row[i];
      switch (sqlite3_column_type(st, i)) {
        case SQLITE_INTEGER:
          cell.type = FIELD_INTEGER;
          cell.l = sqlite3_column_int64(st, i);
          break;
        case SQLITE_FLOAT:
          cell.type = FIELD_FLOAT;
          cell.d = sqlite3_column_double(st, i);
          break;
        case SQLITE_TEXT: {
          cell.type = FIELD_STRING;
          const unsigned char* t = sqlite3_column_text(st, i);
          int n = sqlite3_column_bytes(st, i);
          if (t != nullptr) cell.s.assign(reinterpret_cast<const char*>(t), n);
          rowBytes += cell.s.size();
          break;
        }
        case SQLITE_BLOB: {
          cell.type = FIELD_BLOB;
          const void* b = sqlite3_column_blob(st, i);
          int n = sqlite3_column_bytes(st, i);
          if (b != nullptr) {
            cell.blob.resize(n);
            memcpy(cell.blob.data(), b, n);
          }
          rowBytes += cell.blob.size();
          break;
        }
        default:
          cell.type = FIELD_NULL;
          break;
      }
    }
    w->rows.push_back(std::move(row));
    w->bytes += rowBytes + numColumns * sizeof(Cell);

    // The Java side re-queries with a new startPos when the window fills up; honour the
    // size budget so a huge table cannot exhaust the heap.
    if (w->bytes >= w->maxSize && rowIndex > requiredPos) {
      if (!countAllRows) break;
      stoppedEarly = true;
    }
  }

  if (rc != SQLITE_DONE && rc != SQLITE_ROW) {
    ThrowSqlite(env, c->db, rc, "while stepping into cursor window");
    sqlite3_reset(st);
    return 0;
  }
  sqlite3_reset(st);
  return (static_cast<jlong>(startPos) << 32) | static_cast<jlong>(totalRows);
}

// ------------------------------------------------------------ global / debug

jint nativeReleaseMemory(JNIEnv*, jclass) { return sqlite3_release_memory(0x7fffffff); }

void nativeGetPagerStats(JNIEnv* env, jclass, jobject statsObj) {
  jclass cls = env->GetObjectClass(statsObj);
  struct { const char* name; jlong value; } fields[] = {
      {"totalBytes", 0}, {"referencedBytes", 0}, {"memoryUsed", sqlite3_memory_used()},
      {"largestMemAlloc", sqlite3_memory_highwater(0)}, {"pageCacheOverflow", 0},
  };
  for (auto& f : fields) {
    jfieldID id = env->GetFieldID(cls, f.name, "J");
    if (id != nullptr) {
      env->SetLongField(statsObj, id, f.value);
    } else {
      env->ExceptionClear();
    }
  }
}

// ------------------------------------------------------------------ tables

const JNINativeMethod kConnectionMethods[] = {
    {"nativeOpen", "(Ljava/lang/String;ILjava/lang/String;ZZII)J", (void*)nativeOpen},
    {"nativeClose", "(J)V", (void*)nativeClose},
    {"nativeRegisterCustomScalarFunction",
     "(JLjava/lang/String;Ljava/util/function/UnaryOperator;)V",
     (void*)nativeRegisterCustomScalarFunction},
    {"nativeRegisterCustomAggregateFunction",
     "(JLjava/lang/String;Ljava/util/function/BinaryOperator;)V",
     (void*)nativeRegisterCustomAggregateFunction},
    {"nativeRegisterLocalizedCollators", "(JLjava/lang/String;)V",
     (void*)nativeRegisterLocalizedCollators},
    {"nativePrepareStatement", "(JLjava/lang/String;)J", (void*)nativePrepareStatement},
    {"nativeFinalizeStatement", "(JJ)V", (void*)nativeFinalizeStatement},
    {"nativeGetParameterCount", "(JJ)I", (void*)nativeGetParameterCount},
    {"nativeIsReadOnly", "(JJ)Z", (void*)nativeIsReadOnly},
    {"nativeGetColumnCount", "(JJ)I", (void*)nativeGetColumnCount},
    {"nativeGetColumnName", "(JJI)Ljava/lang/String;", (void*)nativeGetColumnName},
    {"nativeBindNull", "(JJI)V", (void*)nativeBindNull},
    {"nativeBindLong", "(JJIJ)V", (void*)nativeBindLong},
    {"nativeBindDouble", "(JJID)V", (void*)nativeBindDouble},
    {"nativeBindString", "(JJILjava/lang/String;)V", (void*)nativeBindString},
    {"nativeBindBlob", "(JJI[B)V", (void*)nativeBindBlob},
    {"nativeResetStatementAndClearBindings", "(JJ)V",
     (void*)nativeResetStatementAndClearBindings},
    {"nativeExecute", "(JJZ)V", (void*)nativeExecute},
    {"nativeExecuteForLong", "(JJ)J", (void*)nativeExecuteForLong},
    {"nativeExecuteForString", "(JJ)Ljava/lang/String;", (void*)nativeExecuteForString},
    {"nativeExecuteForBlobFileDescriptor", "(JJ)I", (void*)nativeExecuteForBlobFileDescriptor},
    {"nativeExecuteForChangedRowCount", "(JJ)I", (void*)nativeExecuteForChangedRowCount},
    {"nativeExecuteForLastInsertedRowId", "(JJ)J", (void*)nativeExecuteForLastInsertedRowId},
    {"nativeExecuteForCursorWindow", "(JJJIIZ)J", (void*)nativeExecuteForCursorWindow},
    {"nativeGetDbLookaside", "(J)I", (void*)nativeGetDbLookaside},
    {"nativeCancel", "(J)V", (void*)nativeCancel},
    {"nativeResetCancel", "(JZ)V", (void*)nativeResetCancel},
};

const JNINativeMethod kWindowMethods[] = {
    {"nativeCreate", "(Ljava/lang/String;I)J", (void*)cwCreate},
    {"nativeCreateFromParcel", "(Landroid/os/Parcel;)J", (void*)cwCreateFromParcel},
    {"nativeDispose", "(J)V", (void*)cwDispose},
    {"nativeWriteToParcel", "(JLandroid/os/Parcel;)V", (void*)cwWriteToParcel},
    {"nativeGetName", "(J)Ljava/lang/String;", (void*)cwGetName},
    {"nativeGetBlob", "(JII)[B", (void*)cwGetBlob},
    {"nativeGetString", "(JII)Ljava/lang/String;", (void*)cwGetString},
    {"nativeCopyStringToBuffer", "(JIILandroid/database/CharArrayBuffer;)V",
     (void*)cwCopyStringToBuffer},
    {"nativePutBlob", "(J[BII)Z", (void*)cwPutBlob},
    {"nativePutString", "(JLjava/lang/String;II)Z", (void*)cwPutString},
    {"nativeClear", "(J)V", (void*)cwClear},
    {"nativeGetNumRows", "(J)I", (void*)cwGetNumRows},
    {"nativeSetNumColumns", "(JI)Z", (void*)cwSetNumColumns},
    {"nativeAllocRow", "(J)Z", (void*)cwAllocRow},
    {"nativeFreeLastRow", "(J)V", (void*)cwFreeLastRow},
    {"nativeGetType", "(JII)I", (void*)cwGetType},
    {"nativeGetLong", "(JII)J", (void*)cwGetLong},
    {"nativeGetDouble", "(JII)D", (void*)cwGetDouble},
    {"nativePutLong", "(JJII)Z", (void*)cwPutLong},
    {"nativePutDouble", "(JDII)Z", (void*)cwPutDouble},
    {"nativePutNull", "(JII)Z", (void*)cwPutNull},
};

const JNINativeMethod kGlobalMethods[] = {
    {"nativeReleaseMemory", "()I", (void*)nativeReleaseMemory},
};

const JNINativeMethod kDebugMethods[] = {
    {"nativeGetPagerStats", "(Landroid/database/sqlite/SQLiteDebug$PagerStats;)V",
     (void*)nativeGetPagerStats},
};

int RegisterOn(JNIEnv* env, const char* className, const JNINativeMethod* methods, int count) {
  jclass c = env->FindClass(className);
  if (c == nullptr) {
    env->ExceptionClear();
    WL_LOG("%s NOT FOUND, skipping %d methods\n", className, count);
    return -1;
  }
  int rc = env->RegisterNatives(c, methods, count);
  if (rc != JNI_OK || env->ExceptionCheck()) {
    env->ExceptionDescribe();
    env->ExceptionClear();
    WL_LOG("RegisterNatives(%s) FAILED rc=%d\n", className, rc);
    env->DeleteLocalRef(c);
    return -1;
  }
  env->DeleteLocalRef(c);
  WL_LOG("registered %d natives on %s\n", count, className);
  return 0;
}

// ------------------------------------------------- unrun <clinit> repair
//
// This imageless runtime stamps boot-classpath classes kInitialized without ever
// running their <clinit>, so their statics stay null and blow up far from the cause.
// libart's fix107 handles that with a hardcoded force-<clinit> list, but the list only
// covers classes we have already been bitten by, and rebuilding libart costs a full
// cross-compile cycle.  Repairing from here is the cheap loop: the registrar below is
// the earliest point in the child where we hold a JNIEnv, which is well before
// ActivityThread.main and therefore before anything an app can touch.
//
// Each entry is gated on a probe field actually being null, so an entry that is wrong
// (or a class whose <clinit> genuinely did run) is a no-op rather than a double-init.
//
// The permanent home for these is libart's fix107 list; see 07-deploy-lessons.md.
struct StaticRepair {
  const char* cls;
  const char* probeField;
  const char* probeSig;
};

const StaticRepair kRepairs[] = {
    // SharedPreferencesImpl.loadFromDisk closes its stream through IoUtils.closeQuietly;
    // BufferedInputStream.close() drives bufUpdater.compareAndSet, so a null bufUpdater
    // NPEs on the prefs load thread.  That exception is stashed and rethrown on the main
    // thread as IllegalStateException out of awaitLoadedLocked, which is what kills
    // MainActivity (via DynamicColors' onActivityPreCreated reading a boolean pref).
    {"java/io/BufferedInputStream", "bufUpdater",
     "Ljava/util/concurrent/atomic/AtomicReferenceFieldUpdater;"},
    // Every servertransaction item is pooled: obtain() reads sPoolMap and recycle()
    // writes it, and TransactionExecutor recycles the whole transaction when it is done.
    // We hand-build a ResumeActivityItem below, so both ends have to work.
    {"android/app/servertransaction/ObjectPool", "sPoolSync", "Ljava/lang/Object;"},
};

void RepairStatics(JNIEnv* env) {
  for (const StaticRepair& r : kRepairs) {
    jclass c = env->FindClass(r.cls);
    if (c == nullptr) {
      env->ExceptionClear();
      WL_LOG("clinit-repair: %s not found\n", r.cls);
      continue;
    }
    jfieldID probe = env->GetStaticFieldID(c, r.probeField, r.probeSig);
    if (probe == nullptr) {
      env->ExceptionClear();
      WL_LOG("clinit-repair: %s has no %s\n", r.cls, r.probeField);
      env->DeleteLocalRef(c);
      continue;
    }
    jobject value = env->GetStaticObjectField(c, probe);
    if (value != nullptr) {
      env->DeleteLocalRef(value);
      env->DeleteLocalRef(c);
      continue;  // already initialised, leave it alone
    }
    jmethodID clinit = env->GetStaticMethodID(c, "<clinit>", "()V");
    if (clinit == nullptr) {
      env->ExceptionClear();
      WL_LOG("clinit-repair: %s.%s is null but there is no <clinit> to run\n", r.cls,
             r.probeField);
      env->DeleteLocalRef(c);
      continue;
    }
    env->CallStaticVoidMethod(c, clinit);
    if (env->ExceptionCheck()) {
      env->ExceptionDescribe();
      env->ExceptionClear();
      WL_LOG("clinit-repair: %s <clinit> THREW\n", r.cls);
      env->DeleteLocalRef(c);
      continue;
    }
    value = env->GetStaticObjectField(c, probe);
    WL_LOG("clinit-repair: ran %s.<clinit>, %s is now %s\n", r.cls, r.probeField,
           (value != nullptr) ? "set" : "STILL NULL");
    if (value != nullptr) env->DeleteLocalRef(value);
    env->DeleteLocalRef(c);
  }
}

bool ForceClinit(JNIEnv* env, const char* cls) {
  jclass c = env->FindClass(cls);
  if (c == nullptr) {
    env->ExceptionClear();
    return false;
  }
  jmethodID clinit = env->GetStaticMethodID(c, "<clinit>", "()V");
  if (clinit == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(c);
    return false;
  }
  env->CallStaticVoidMethod(c, clinit);
  bool ok = !env->ExceptionCheck();
  if (!ok) env->ExceptionClear();
  env->DeleteLocalRef(c);
  return ok;
}

// Charset.forName("UTF-8") comes back null on this runtime, so String.getBytes(String)
// raises UnsupportedEncodingException and every Uri.Builder.appendQueryParameter dies.
// Noice loses two whole Hilt singletons to it (SubscriptionRepository,
// StripeSubscriptionBillingProvider), each swallowed as a "tolerated clinit failure".
// Probe it, and if it is broken try the usual <clinit> suspects before giving up.
void RepairCharset(JNIEnv* env) {
  jclass cs = env->FindClass("java/nio/charset/Charset");
  if (cs == nullptr) {
    env->ExceptionClear();
    WL_LOG("charset: no java/nio/charset/Charset\n");
    return;
  }
  jmethodID forName = env->GetStaticMethodID(cs, "forName",
                                             "(Ljava/lang/String;)Ljava/nio/charset/Charset;");
  if (forName == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(cs);
    return;
  }
  const char* kSuspects[] = {
      "sun/nio/cs/StandardCharsets",
      "java/nio/charset/Charset",
      "java/nio/charset/StandardCharsets",
      "libcore/icu/ICU",
  };
  for (int round = 0; round < 2; round++) {
    jstring name = env->NewStringUTF("UTF-8");
    jobject got = env->CallStaticObjectMethod(cs, forName, name);
    bool threw = env->ExceptionCheck();
    if (threw) env->ExceptionClear();
    env->DeleteLocalRef(name);
    if (got != nullptr) {
      env->DeleteLocalRef(got);
      WL_LOG("charset: Charset.forName(UTF-8) ok%s\n", round ? " after <clinit> repair" : "");
      env->DeleteLocalRef(cs);
      return;
    }
    WL_LOG("charset: Charset.forName(UTF-8) -> %s\n", threw ? "THREW" : "null");
    if (round != 0) break;
    for (const char* s : kSuspects) {
      WL_LOG("charset: forcing %s.<clinit> -> %s\n", s, ForceClinit(env, s) ? "ok" : "no");
    }
  }
  env->DeleteLocalRef(cs);
}

// java.security.Security is another <clinit> casualty, and it is a lethal one: its
// static spiMap/props are null, so the very first getSpiClass call NPEs --
//   java.lang.NullPointerException: ... 'java.lang.Object java.util.Map.get(...)'
//     at java.security.Security.getSpiClass(Security.java:603)
//     at java.security.MessageDigest.getInstance(MessageDigest.java:211)
//     at okio.ByteString.b -> okhttp3.a$b.a(Cache.kt) -> k8.a.a(CacheInterceptor.kt)
// That lands on OkHttp's Dispatcher pool thread, where nothing catches it, and the
// substrate's default handler tears the whole process down ("FATAL EXCEPTION in
// i8.s Dispatcher") a second before the activity would have added its window.
// It is also why CertificateFactory.getInstance("X.509") was unavailable earlier.
//
// BUT the repair is worse than the disease here, so it is probe-only unless
// WL_REPAIR_SECURITY is set.  Running Security.<clinit> populates the provider
// properties, and the next thing to read them walks
//   Providers.<clinit> -> ProviderList.removeInvalid -> loadAll
//     -> new com.android.org.conscrypt.OpenSSLProvider -> NativeCrypto.<clinit>
//     -> System.loadLibrary("javacrypto")
// and this substrate ships no libjavacrypto.so.  ProviderConfig.doLoadProvider only
// catches Exception, so the UnsatisfiedLinkError escapes and takes down whoever
// touched crypto first -- which turned out to be handleBindApplication, i.e. the app
// died before the activity even launched.  Leaving Security uninitialised keeps the
// failure a mere NPE, and DisarmKillHandler below keeps that NPE non-fatal.
void RepairSecurity(JNIEnv* env) {
  if (getenv("WL_REPAIR_SECURITY") == nullptr) {
    // Not even the probe: MessageDigest.getInstance is itself what walks into
    // Providers.<clinit> once Security is initialised, so probing can pull the trigger.
    WL_LOG("security: java.security left alone (set WL_REPAIR_SECURITY to try repairing)\n");
    return;
  }
  const bool repair = true;
  jclass md = env->FindClass("java/security/MessageDigest");
  if (md == nullptr) {
    env->ExceptionClear();
    WL_LOG("security: no java/security/MessageDigest\n");
    return;
  }
  jmethodID getInstance = env->GetStaticMethodID(
      md, "getInstance", "(Ljava/lang/String;)Ljava/security/MessageDigest;");
  if (getInstance == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(md);
    return;
  }
  const char* kSuspects[] = {
      "java/security/Security",
      "sun/security/jca/Providers",
      "sun/security/jca/ProviderList",
      "java/security/Provider",
      "java/security/MessageDigest",
  };
  for (int round = 0; round < 2; round++) {
    // MD5 is what okhttp's cache key uses, so probing it exercises the exact path.
    jstring algo = env->NewStringUTF("MD5");
    jobject got = env->CallStaticObjectMethod(md, getInstance, algo);
    bool threw = env->ExceptionCheck();
    if (threw) env->ExceptionClear();
    env->DeleteLocalRef(algo);
    if (got != nullptr) {
      env->DeleteLocalRef(got);
      WL_LOG("security: MessageDigest.getInstance(MD5) ok%s\n",
             round ? " after <clinit> repair" : "");
      env->DeleteLocalRef(md);
      return;
    }
    WL_LOG("security: MessageDigest.getInstance(MD5) -> %s%s\n", threw ? "THREW" : "null",
           repair ? "" : " (left broken on purpose; set WL_REPAIR_SECURITY to try)");
    if (round != 0 || !repair) break;
    for (const char* s : kSuspects) {
      WL_LOG("security: forcing %s.<clinit> -> %s\n", s, ForceClinit(env, s) ? "ok" : "no");
    }
  }
  env->DeleteLocalRef(md);
}

// ------------------------------------------------ substrate bindService bridge
//
// adapter.activity.ActivityManagerAdapter.nativeConnectAbility(String, String, int) is
// the substrate's bindService bridge, and calling it aborts the whole runtime:
//   JNI ERROR (app bug): jstring is an invalid IndirectRefKind(0): 0x1435fbe0
//   in call to GetStringUTFChars from ...nativeConnectAbility
// Noice hits it as soon as the UI is up, from SoundPlaybackService$Controller.getState's
// bindServiceCallbackFlow, so it is the last thing between us and a rendered screen.
//
// These natives are resolved lazily by symbol lookup rather than RegisterNatives, so
// binding our own first simply wins.  The stub logs the raw argument words -- that says
// whether ART handed the substrate good references (making this the substrate's bug) or
// raw heap pointers (making it ours) -- and reports a plausible connection id so
// ContextImpl.bindServiceCommon returns true instead of throwing SecurityException.
jint WlConnectAbility(JNIEnv*, jclass, jstring bundleName, jstring abilityName, jint flags) {
  WL_LOG("connectAbility: bundle=%p ability=%p flags=%d (stubbed, not forwarded)\n",
         static_cast<void*>(bundleName), static_cast<void*>(abilityName),
         static_cast<int>(flags));
  return 1;
}

jint WlDisconnectAbility(JNIEnv*, jclass, jint connectionId) {
  WL_LOG("disconnectAbility: id=%d (stubbed)\n", static_cast<int>(connectionId));
  return 0;
}

const JNINativeMethod kAdapterStubs[] = {
    {"nativeConnectAbility", "(Ljava/lang/String;Ljava/lang/String;I)I",
     reinterpret_cast<void*>(WlConnectAbility)},
    {"nativeDisconnectAbility", "(I)I", reinterpret_cast<void*>(WlDisconnectAbility)},
};

// ------------------------------------------------------ the adapter bridge itself
//
// liboh_adapter_bridge.so exports AdapterBridge::initialize(JNIEnv*) plus a registrar per
// adapter, and on this build nothing ever calls them -- the same "startReg never runs"
// hole libart's fix104 papers over for the platform libraries.  Two consequences:
//
//  * the bridge never gets a JavaVM, so every adapter that needs to call back into Java
//    logs "Failed to get JNIEnv in constructor".  WindowCallbackAdapter is one of them,
//    and without it IWindowManager::CreateWindow goes out with no usable callback object;
//    the transaction is rejected at the proxy (IPC error 1) before it ever reaches the
//    window service, which surfaces as WMError 1005 -> ADD_INVALID_DISPLAY -> the app
//    dying with InvalidDisplayException out of the first wm.addView.
//  * the adapters' natives fall through to lazy symbol resolution instead of
//    RegisterNatives, and that path mangles their arguments (see WlConnectAbility).
//
// Calling them by hand fixes both.  Done in the child rather than the daemon: whatever
// the bridge caches on the way up (IPC proxies in particular) has to belong to the
// process that will actually use it.
void InitAdapterBridge(JNIEnv* env) {
  static const char* kPaths[] = {"liboh_adapter_bridge.so",
                                 "/system/android/lib64/liboh_adapter_bridge.so"};
  void* h = nullptr;
  for (const char* p : kPaths) {
    h = dlopen(p, RTLD_NOW | RTLD_NOLOAD);
    if (h != nullptr) break;
  }
  if (h == nullptr) {
    WL_LOG("bridge: liboh_adapter_bridge.so is not loaded\n");
    return;
  }
  WL_LOG("bridge: handle=%p\n", h);
  // JNI_OnLoad is the library's real entry point: it stores the JavaVM on the
  // AdapterBridge singleton, registers the Skia codecs, and runs all six adapter
  // registrars.  It never runs here because nothing loads this library through
  // System.loadLibrary -- it is pulled in as an ordinary native dependency, and the
  // dynamic loader does not call JNI_OnLoad.  Calling it by hand is the whole fix.
  //
  // AdapterBridge::initialize is deliberately NOT called: it faults on this build (the
  // child dies on SIGSEGV), and it only caches LifecycleAdapter/DataShare method IDs --
  // nothing the window path needs.
  using OnLoadFn = jint (*)(JavaVM*, void*);
  OnLoadFn onLoad = reinterpret_cast<OnLoadFn>(dlsym(h, "JNI_OnLoad"));
  if (onLoad == nullptr) {
    WL_LOG("bridge: JNI_OnLoad not exported\n");
    return;
  }
  JavaVM* vm = nullptr;
  if (env->GetJavaVM(&vm) != JNI_OK || vm == nullptr) {
    WL_LOG("bridge: no JavaVM to hand to JNI_OnLoad\n");
    return;
  }
  WL_LOG("bridge: calling JNI_OnLoad(vm=%p)\n", static_cast<void*>(vm));
  jint version = onLoad(vm, nullptr);
  if (env->ExceptionCheck()) {
    env->ExceptionDescribe();
    env->ExceptionClear();
  }
  WL_LOG("bridge: JNI_OnLoad returned 0x%x\n", static_cast<unsigned>(version));
}

void InstallAdapterStubs(JNIEnv* env) {
  if (getenv("WL_NO_CONNECT_STUB") != nullptr) {
    WL_LOG("connectAbility: stub disabled by WL_NO_CONNECT_STUB\n");
    return;
  }
  jclass c = env->FindClass("adapter/activity/ActivityManagerAdapter");
  if (c == nullptr) {
    env->ExceptionClear();
    WL_LOG("connectAbility: adapter.activity.ActivityManagerAdapter not found\n");
    return;
  }
  jint rc = env->RegisterNatives(c, kAdapterStubs,
                                 static_cast<jint>(sizeof(kAdapterStubs) / sizeof(kAdapterStubs[0])));
  if (rc != JNI_OK || env->ExceptionCheck()) {
    env->ExceptionClear();
    WL_LOG("connectAbility: RegisterNatives failed rc=%d\n", static_cast<int>(rc));
  } else {
    WL_LOG("connectAbility: took over connect/disconnect on ActivityManagerAdapter\n");
  }
  env->DeleteLocalRef(c);
}

bool g_statics_repaired = false;

void EnsureStaticsRepaired(JNIEnv* env) {
  if (g_statics_repaired) return;
  g_statics_repaired = true;  // set first: a repair that throws must not retry forever
  RepairStatics(env);
  RepairCharset(env);
  RepairSecurity(env);
  InstallAdapterStubs(env);
}

// Backstop for every <clinit> casualty we have not found yet.  The substrate installs
// an Android-style KillApplicationHandler as the default uncaught-exception handler, so
// one NPE on any background thread (OkHttp's dispatcher, a Hilt init worker, ...) takes
// the whole process down.  With no default handler, ThreadGroup.uncaughtException just
// prints the trace and only that thread dies, which is what we want while bringing the
// UI up: the failures stay visible in the log but stop being fatal.
void DisarmKillHandler(JNIEnv* env) {
  static bool announced = false;
  jclass th = env->FindClass("java/lang/Thread");
  if (th == nullptr) {
    env->ExceptionClear();
    return;
  }
  jmethodID get = env->GetStaticMethodID(th, "getDefaultUncaughtExceptionHandler",
                                         "()Ljava/lang/Thread$UncaughtExceptionHandler;");
  jmethodID set = env->GetStaticMethodID(th, "setDefaultUncaughtExceptionHandler",
                                         "(Ljava/lang/Thread$UncaughtExceptionHandler;)V");
  if (get == nullptr || set == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(th);
    return;
  }
  jobject cur = env->CallStaticObjectMethod(th, get);
  if (env->ExceptionCheck()) env->ExceptionClear();
  if (cur == nullptr) {
    env->DeleteLocalRef(th);
    return;  // already disarmed
  }
  if (!announced) {
    announced = true;
    jclass ocls = env->GetObjectClass(cur);
    jclass clsCls = env->FindClass("java/lang/Class");
    jmethodID getName = clsCls ? env->GetMethodID(clsCls, "getName", "()Ljava/lang/String;")
                               : nullptr;
    if (clsCls != nullptr) env->DeleteLocalRef(clsCls);
    jstring nm = getName ? static_cast<jstring>(env->CallObjectMethod(ocls, getName)) : nullptr;
    if (env->ExceptionCheck()) env->ExceptionClear();
    const char* utf = nm ? env->GetStringUTFChars(nm, nullptr) : nullptr;
    WL_LOG("ueh: dropping default uncaught-exception handler %s\n", utf ? utf : "?");
    if (utf != nullptr) env->ReleaseStringUTFChars(nm, utf);
    if (nm != nullptr) env->DeleteLocalRef(nm);
    env->DeleteLocalRef(ocls);
  }
  env->DeleteLocalRef(cur);
  env->CallStaticVoidMethod(th, set, nullptr);
  if (env->ExceptionCheck()) env->ExceptionClear();
  env->DeleteLocalRef(th);
}

// ------------------------------------------------------- app theme stopgap
//
// STOPGAP, and it should be deleted the moment libart can be rebuilt.
//
// Noice's manifest says <application android:theme="@0x7f14023d">, MainActivity
// declares no theme of its own, so ActivityInfo.getThemeResource() must fall through to
// ApplicationInfo.theme.  Two things go wrong here: the substrate's own [G2.5-PIB] path
// zeroes ApplicationInfo.icon/iconRes/labelRes/theme, and libart's fix102 AXML parser
// fails to recover it -- it logs "manifest appTheme=0 (no app android:theme)" even
// though the attribute is right there, because android:theme is a TYPE_REFERENCE and
// the parser only picks up the string-valued attributes (className, appComponentFactory
// and friends all come through fine).  With theme == 0 ActivityThread never calls
// setTheme, the activity lands on Theme.DeviceDefault, and AppCompat throws
// "You need to use a Theme.AppCompat theme (or descendant) with this activity."
//
// The real fix belongs in wl_axml_parser.h.  Until then this thread writes the value
// back into the one ApplicationInfo we can reach from JNI.  It is opt-in and scoped to
// a single package so it cannot silently re-theme anything else:
//
//     WL_APP_THEME=com.github.ashutoshgngwr.noice:0x7f14023d
//
// It keeps rewriting rather than writing once, because [G2.5-PIB] re-zeroes the struct
// several times during startup.
struct ThemeOverride {
  char pkg[192];
  jint theme;
  char appClass[256];  // ApplicationInfo.className; empty when WL_APP_CLASS is unset
  jint targetSdk;      // ApplicationInfo.targetSdkVersion; 0 leaves it alone
  bool forceSoftware;  // clear FLAG_HARDWARE_ACCELERATED so ViewRootImpl draws in software
  JavaVM* vm;
};

ThemeOverride g_theme;

// Reads pkg:0xTHEME out of the environment.  Returns false if unset or malformed.
bool ParseThemeOverride(ThemeOverride* out) {
  const char* spec = getenv("WL_APP_THEME");
  if (spec == nullptr || *spec == '\0') return false;
  const char* colon = strrchr(spec, ':');
  if (colon == nullptr || colon == spec) {
    WL_LOG("theme: WL_APP_THEME=\"%s\" is not pkg:0xTHEME\n", spec);
    return false;
  }
  size_t n = static_cast<size_t>(colon - spec);
  if (n >= sizeof(out->pkg)) return false;
  memcpy(out->pkg, spec, n);
  out->pkg[n] = '\0';
  out->theme = static_cast<jint>(strtoul(colon + 1, nullptr, 0));
  if (out->theme == 0) {
    WL_LOG("theme: WL_APP_THEME has no usable resource id\n");
    return false;
  }
  const char* appClass = getenv("WL_APP_CLASS");
  if (appClass != nullptr && *appClass != '\0') {
    size_t len = strlen(appClass);
    if (len < sizeof(out->appClass)) memcpy(out->appClass, appClass, len + 1);
  }
  const char* sdk = getenv("WL_APP_TARGET_SDK");
  if (sdk != nullptr && *sdk != '\0') out->targetSdk = static_cast<jint>(atoi(sdk));
  out->forceSoftware = getenv("WL_FORCE_SOFTWARE_RENDER") != nullptr;
  return true;
}

// The substrate's manifest parser misses <application android:name= > the same way it
// misses android:theme, so ApplicationInfo.className stays null and
// LoadedApk.makeApplication() builds a bare android.app.Application.  Noice is a Hilt
// app: MainActivity is an @AndroidEntryPoint, so the first thing its onCreate does is
// ask the Application for the generated component, and it dies with
//   IllegalStateException: Given component holder class android.app.Application
//   does not implement interface z6.a or interface z6.b
// Writing the real class name is enough, and this fires early enough to matter -- the
// theme patch already lands before the app's own dex is opened, which is well ahead of
// makeApplication().
int PatchClassName(JNIEnv* env, jobject appInfo, jfieldID classField) {
  if (classField == nullptr || g_theme.appClass[0] == '\0') return 0;
  jstring cur = static_cast<jstring>(env->GetObjectField(appInfo, classField));
  bool same = false;
  if (cur != nullptr) {
    const char* c = env->GetStringUTFChars(cur, nullptr);
    if (c != nullptr) {
      same = strcmp(c, g_theme.appClass) == 0;
      env->ReleaseStringUTFChars(cur, c);
    }
    env->DeleteLocalRef(cur);
  }
  if (same) return 0;
  jstring want = env->NewStringUTF(g_theme.appClass);
  if (want == nullptr) {
    env->ExceptionClear();
    return 0;
  }
  env->SetObjectField(appInfo, classField, want);
  env->DeleteLocalRef(want);
  return 1;
}

// Writes theme into `appInfo` if it belongs to the target package.  Returns 1 if it
// changed something.
// ApplicationInfo.FLAG_HARDWARE_ACCELERATED
constexpr jint kFlagHardwareAccelerated = 1 << 13;

int PatchApplicationInfo(JNIEnv* env, jobject appInfo) {
  if (appInfo == nullptr) return 0;
  jclass cls = env->GetObjectClass(appInfo);
  jfieldID pkgField = env->GetFieldID(cls, "packageName", "Ljava/lang/String;");
  jfieldID themeField = env->GetFieldID(cls, "theme", "I");
  jfieldID classField = env->GetFieldID(cls, "className", "Ljava/lang/String;");
  if (classField == nullptr) env->ExceptionClear();
  jfieldID sdkField = env->GetFieldID(cls, "targetSdkVersion", "I");
  if (sdkField == nullptr) env->ExceptionClear();
  jfieldID flagsField = env->GetFieldID(cls, "flags", "I");
  if (flagsField == nullptr) env->ExceptionClear();
  if (pkgField == nullptr || themeField == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(cls);
    return 0;
  }
  int changed = 0;
  jstring pkg = static_cast<jstring>(env->GetObjectField(appInfo, pkgField));
  if (pkg != nullptr) {
    const char* p = env->GetStringUTFChars(pkg, nullptr);
    if (p != nullptr) {
      if (strcmp(p, g_theme.pkg) == 0) {
        if (env->GetIntField(appInfo, themeField) != g_theme.theme) {
          env->SetIntField(appInfo, themeField, g_theme.theme);
          changed = 1;
        }
        changed += PatchClassName(env, appInfo, classField);
        // ContextImpl.getSharedPreferences guards credential-encrypted storage behind
        // `targetSdkVersion >= O`, and the guard itself calls
        // getSystemService(UserManager.class).isUserUnlockingOrUnlocked(...).  There is
        // no "user" service on this board, so that returns null and every single
        // getSharedPreferences() call NPEs -- which kills NoiceApplication.onCreate the
        // moment Hilt builds SettingsRepository.  Reporting a pre-O target skips the
        // guard outright; there is nothing to unlock on a board with no lock screen.
        if (g_theme.targetSdk > 0 && sdkField != nullptr &&
            env->GetIntField(appInfo, sdkField) != g_theme.targetSdk) {
          env->SetIntField(appInfo, sdkField, g_theme.targetSdk);
          changed = 1;
        }
        // WL_FORCE_SOFTWARE_RENDER: drop ApplicationInfo.FLAG_HARDWARE_ACCELERATED.
        // Activity.attach copies this bit into the window's
        // WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED, which is the single
        // input to ViewRootImpl.enableHardwareAcceleration -- clear it and the whole
        // hwui path is skipped in favour of drawSoftware() (lockCanvas + View.draw +
        // unlockCanvasAndPost).  Worth having because this board's RenderThread is
        // created but never accumulates any CPU time: the frame never reaches it.
        if (g_theme.forceSoftware && flagsField != nullptr) {
          jint flags = env->GetIntField(appInfo, flagsField);
          if ((flags & kFlagHardwareAccelerated) != 0) {
            env->SetIntField(appInfo, flagsField, flags & ~kFlagHardwareAccelerated);
            changed = 1;
          }
        }
      }
      env->ReleaseStringUTFChars(pkg, p);
    }
    env->DeleteLocalRef(pkg);
  }
  env->DeleteLocalRef(cls);
  return changed;
}

// Follows obj.<field> and returns it, or null (with any exception cleared).
jobject GetObjField(JNIEnv* env, jobject obj, const char* fieldName, const char* sig) {
  if (obj == nullptr) return nullptr;
  jclass cls = env->GetObjectClass(obj);
  jfieldID f = env->GetFieldID(cls, fieldName, sig);
  env->DeleteLocalRef(cls);
  if (f == nullptr) {
    env->ExceptionClear();
    return nullptr;
  }
  return env->GetObjectField(obj, f);
}

// The ApplicationInfo hanging off the launch's ActivityInfo is a *different* instance
// from ActivityThread.mBoundApplication.appInfo -- the substrate's [G2.5-PIB] path mints
// a fresh, theme-zeroed one per call -- so patching the bound one is not enough.
//
// The ActivityInfo we actually need is reachable, though: startLaunchActivity runs on a
// helper thread and posts a ClientTransaction to the main looper, while the main thread
// is still inside handleBindApplication running Application.onCreate (Hilt, Room -- over
// a second here).  During that window the transaction is just a queued Message, so walk
// the queue and set ActivityInfo.theme directly, which skips the applicationInfo
// question entirely.
struct LaunchQueueRefs {
  jclass looper = nullptr;
  jmethodID getMainLooper = nullptr;
  jfieldID looperQueue = nullptr;
  jfieldID queueMessages = nullptr;
  jfieldID messageNext = nullptr;
  jfieldID messageObj = nullptr;
  jclass clientTransaction = nullptr;
  jfieldID transactionCallbacks = nullptr;
  jclass launchItem = nullptr;
  jfieldID launchInfo = nullptr;
  jclass list = nullptr;
  jmethodID listSize = nullptr;
  jmethodID listGet = nullptr;
  jfieldID activityTheme = nullptr;
  jfieldID activityPackage = nullptr;
  // Lifecycle-state injection (see InjectResumeRequest).  Kept out of `ok` so that a
  // build whose servertransaction package differs still gets the theme fix.
  jfieldID transactionLifecycle = nullptr;
  jmethodID setLifecycleRequest = nullptr;
  jclass resumeItem = nullptr;
  jmethodID resumeObtain = nullptr;
  jfieldID resumeIsForward = nullptr;
  bool canResume = false;
  bool ok = false;
};

LaunchQueueRefs g_q;

jclass GlobalClass(JNIEnv* env, const char* name) {
  jclass local = env->FindClass(name);
  if (local == nullptr) {
    env->ExceptionClear();
    WL_LOG("theme: class %s not found\n", name);
    return nullptr;
  }
  jclass global = static_cast<jclass>(env->NewGlobalRef(local));
  env->DeleteLocalRef(local);
  return global;
}

void InitLaunchQueueRefs(JNIEnv* env) {
  LaunchQueueRefs q;
  q.looper = GlobalClass(env, "android/os/Looper");
  q.clientTransaction = GlobalClass(env, "android/app/servertransaction/ClientTransaction");
  q.launchItem = GlobalClass(env, "android/app/servertransaction/LaunchActivityItem");
  q.list = GlobalClass(env, "java/util/List");
  jclass messageQueue = env->FindClass("android/os/MessageQueue");
  jclass message = env->FindClass("android/os/Message");
  jclass activityInfo = env->FindClass("android/content/pm/ActivityInfo");
  if (q.looper == nullptr || q.clientTransaction == nullptr || q.launchItem == nullptr ||
      q.list == nullptr || messageQueue == nullptr || message == nullptr ||
      activityInfo == nullptr) {
    env->ExceptionClear();
    return;
  }
  q.getMainLooper = env->GetStaticMethodID(q.looper, "getMainLooper", "()Landroid/os/Looper;");
  q.looperQueue = env->GetFieldID(q.looper, "mQueue", "Landroid/os/MessageQueue;");
  q.queueMessages = env->GetFieldID(messageQueue, "mMessages", "Landroid/os/Message;");
  q.messageNext = env->GetFieldID(message, "next", "Landroid/os/Message;");
  q.messageObj = env->GetFieldID(message, "obj", "Ljava/lang/Object;");
  q.transactionCallbacks = env->GetFieldID(q.clientTransaction, "mActivityCallbacks",
                                           "Ljava/util/List;");
  q.launchInfo = env->GetFieldID(q.launchItem, "mInfo", "Landroid/content/pm/ActivityInfo;");
  q.listSize = env->GetMethodID(q.list, "size", "()I");
  q.listGet = env->GetMethodID(q.list, "get", "(I)Ljava/lang/Object;");
  q.activityTheme = env->GetFieldID(activityInfo, "theme", "I");
  q.activityPackage = env->GetFieldID(activityInfo, "packageName", "Ljava/lang/String;");
  q.transactionLifecycle =
      env->GetFieldID(q.clientTransaction, "mLifecycleStateRequest",
                      "Landroid/app/servertransaction/ActivityLifecycleItem;");
  q.setLifecycleRequest =
      env->GetMethodID(q.clientTransaction, "setLifecycleStateRequest",
                       "(Landroid/app/servertransaction/ActivityLifecycleItem;)V");
  q.resumeItem = GlobalClass(env, "android/app/servertransaction/ResumeActivityItem");
  if (q.resumeItem != nullptr) {
    // Two obtain() overloads exist; the (Z,Z) one leaves mUpdateProcState false, so
    // preExecute never calls back into an activity manager we do not really have.
    q.resumeObtain = env->GetStaticMethodID(
        q.resumeItem, "obtain", "(ZZ)Landroid/app/servertransaction/ResumeActivityItem;");
    if (q.resumeObtain == nullptr) env->ExceptionClear();
    q.resumeIsForward = env->GetFieldID(q.resumeItem, "mIsForward", "Z");
    if (q.resumeIsForward == nullptr) env->ExceptionClear();
  }
  env->DeleteLocalRef(messageQueue);
  env->DeleteLocalRef(message);
  env->DeleteLocalRef(activityInfo);
  if (env->ExceptionCheck()) {
    env->ExceptionClear();
    WL_LOG("theme: could not resolve the launch-queue field set\n");
    return;
  }
  q.ok = q.getMainLooper != nullptr && q.looperQueue != nullptr && q.queueMessages != nullptr &&
         q.messageNext != nullptr && q.messageObj != nullptr &&
         q.transactionCallbacks != nullptr && q.launchInfo != nullptr && q.listSize != nullptr &&
         q.listGet != nullptr && q.activityTheme != nullptr && q.activityPackage != nullptr;
  q.canResume = q.transactionLifecycle != nullptr && q.setLifecycleRequest != nullptr &&
                q.resumeItem != nullptr;
  g_q = q;
  WL_LOG("theme: launch-queue walk %s (resume-injection %s)\n", q.ok ? "ready" : "UNAVAILABLE",
         q.canResume ? "available" : "UNAVAILABLE");
}

// ---------------------------------------------------- missing lifecycle request
//
// The substrate schedules a ClientTransaction carrying only a LaunchActivityItem and
// leaves mLifecycleStateRequest null:
//   [BRIDGED] ScheduleLaunchAbility(recordId=26) -> scheduleTransaction(LaunchActivityItem)
// TransactionExecutor.executeLifecycleState returns immediately when that field is null,
// and LaunchActivityItem.getPostExecutionState() is ON_CREATE, so the activity stops dead
// at onCreate: no onStart, no onResume, and therefore no wm.addView of the decor view.
// That is the black screen -- the app is alive and idle in the looper while OH waits for
// a foreground report that can never come, then declares LIFECYCLE_TIMEOUT.
//
// The real cause is upstream (OH_AbilitySchedAdapter fails to get a JNIEnv in its
// constructor, so the adapter that would drive the transitions is never usable), but the
// transaction is sitting in our queue and is trivially completable: hang a
// ResumeActivityItem off it and the stock executor walks ON_CREATE -> ON_START -> ON_RESUME
// on its own.
jobject MakeResumeItem(JNIEnv* env) {
  jobject item = nullptr;
  if (g_q.resumeObtain != nullptr) {
    item = env->CallStaticObjectMethod(g_q.resumeItem, g_q.resumeObtain, JNI_TRUE, JNI_FALSE);
    if (env->ExceptionCheck()) {
      env->ExceptionClear();
      item = nullptr;
    }
  }
  if (item != nullptr) return item;
  // ObjectPool's statics are prime candidates for the <clinit> plague; if obtain() is
  // unusable, allocate one directly.  The no-arg constructor is empty and every field
  // we care about defaults correctly except mIsForward.
  item = env->AllocObject(g_q.resumeItem);
  if (env->ExceptionCheck()) {
    env->ExceptionClear();
    return nullptr;
  }
  if (item != nullptr && g_q.resumeIsForward != nullptr) {
    env->SetBooleanField(item, g_q.resumeIsForward, JNI_TRUE);
  }
  WL_LOG("lifecycle: ResumeActivityItem.obtain unusable, allocated one directly\n");
  return item;
}

bool g_resume_reported = false;

// Returns true if this transaction now carries a lifecycle state request.
bool InjectResumeRequest(JNIEnv* env, jobject transaction) {
  if (!g_q.canResume) return false;
  jobject existing = env->GetObjectField(transaction, g_q.transactionLifecycle);
  if (existing != nullptr) {
    if (!g_resume_reported) {
      g_resume_reported = true;
      WL_LOG("lifecycle: launch transaction already carries a state request, left alone\n");
    }
    env->DeleteLocalRef(existing);
    return false;
  }
  jobject item = MakeResumeItem(env);
  if (item == nullptr) {
    if (!g_resume_reported) {
      g_resume_reported = true;
      WL_LOG("lifecycle: could not build a ResumeActivityItem\n");
    }
    return false;
  }
  env->CallVoidMethod(transaction, g_q.setLifecycleRequest, item);
  bool ok = !env->ExceptionCheck();
  if (!ok) env->ExceptionClear();
  env->DeleteLocalRef(item);
  if (!g_resume_reported) {
    g_resume_reported = true;
    WL_LOG("lifecycle: launch transaction had no state request; %s ResumeActivityItem\n",
           ok ? "attached a" : "FAILED to attach a");
  }
  return ok;
}

// Returns the number of pending ActivityInfos re-themed.
int PatchPendingLaunches(JNIEnv* env) {
  if (!g_q.ok) return 0;
  jobject looper = env->CallStaticObjectMethod(g_q.looper, g_q.getMainLooper);
  if (env->ExceptionCheck()) { env->ExceptionClear(); return 0; }
  if (looper == nullptr) return 0;
  jobject queue = env->GetObjectField(looper, g_q.looperQueue);
  env->DeleteLocalRef(looper);
  if (queue == nullptr) return 0;

  int patched = 0;
  jobject msg = env->GetObjectField(queue, g_q.queueMessages);
  env->DeleteLocalRef(queue);
  for (int hop = 0; msg != nullptr && hop < 200; hop++) {
    jobject obj = env->GetObjectField(msg, g_q.messageObj);
    if (obj != nullptr) {
      if (env->IsInstanceOf(obj, g_q.clientTransaction)) {
        bool mineHere = false;
        jobject callbacks = env->GetObjectField(obj, g_q.transactionCallbacks);
        if (callbacks != nullptr) {
          jint n = env->CallIntMethod(callbacks, g_q.listSize);
          if (env->ExceptionCheck()) { env->ExceptionClear(); n = 0; }
          for (jint i = 0; i < n; i++) {
            jobject item = env->CallObjectMethod(callbacks, g_q.listGet, i);
            if (env->ExceptionCheck()) { env->ExceptionClear(); continue; }
            if (item == nullptr) continue;
            if (env->IsInstanceOf(item, g_q.launchItem)) {
              jobject info = env->GetObjectField(item, g_q.launchInfo);
              if (info != nullptr) {
                jstring pkg = static_cast<jstring>(env->GetObjectField(info, g_q.activityPackage));
                bool mine = false;
                if (pkg != nullptr) {
                  const char* p = env->GetStringUTFChars(pkg, nullptr);
                  mine = (p != nullptr && strcmp(p, g_theme.pkg) == 0);
                  if (p != nullptr) env->ReleaseStringUTFChars(pkg, p);
                  env->DeleteLocalRef(pkg);
                }
                if (mine) {
                  mineHere = true;
                  if (env->GetIntField(info, g_q.activityTheme) != g_theme.theme) {
                    env->SetIntField(info, g_q.activityTheme, g_theme.theme);
                    patched++;
                  }
                }
                env->DeleteLocalRef(info);
              }
            }
            env->DeleteLocalRef(item);
          }
          env->DeleteLocalRef(callbacks);
        }
        if (mineHere) InjectResumeRequest(env, obj);
      }
      env->DeleteLocalRef(obj);
    }
    jobject next = env->GetObjectField(msg, g_q.messageNext);
    env->DeleteLocalRef(msg);
    msg = next;
  }
  return patched;
}

// ------------------------------------------------------------- OH ability token
//
// createSession takes the OH ability token as a raw pointer out of OhTokenRegistry,
// wraps it back into an sptr and marshals it into IWindowManager::CreateWindow.  On this
// build that transaction is rejected by the driver before it ever reaches the window
// service -- IPCObjectProxy logs "handle:3 error:1", the proxy turns that into
// WM_ERROR_IPC_FAILED (1005), WindowSessionAdapter maps it to ADD_INVALID_DISPLAY, and
// the first wm.addView throws InvalidDisplayException and takes the app with it.
//
// The adapter only passes the token at all because of its "Bug B" change; before that it
// left tokenState_ false and windows were created fine (at the cost of an orphan starting
// window).  So: set the mapping to 0 instead of deleting it.  createSession then takes
// the no-token path, while buildAddDisplayFlags -- which uses the same lookup, non-null
// only -- still returns ADD_FLAG_APP_VISIBLE, and every other caller already guards with
// "ohAddr != null && ohAddr != 0L" and merely logs.
struct TokenZeroRefs {
  jclass registry = nullptr;
  jfieldID androidToOh = nullptr;
  jmethodID mapKeySet = nullptr;
  jmethodID mapPut = nullptr;
  jmethodID mapGet = nullptr;
  jmethodID setToArray = nullptr;
  jobject zero = nullptr;
  bool ok = false;
};

TokenZeroRefs g_tz;

void InitTokenZeroRefs(JNIEnv* env) {
  TokenZeroRefs t;
  t.registry = GlobalClass(env, "adapter/core/OhTokenRegistry");
  if (t.registry == nullptr) return;
  t.androidToOh = env->GetStaticFieldID(t.registry, "sAndroidToOh",
                                        "Ljava/util/concurrent/ConcurrentHashMap;");
  jclass map = env->FindClass("java/util/Map");
  jclass set = env->FindClass("java/util/Set");
  jclass longCls = env->FindClass("java/lang/Long");
  if (t.androidToOh == nullptr || map == nullptr || set == nullptr || longCls == nullptr) {
    env->ExceptionClear();
    WL_LOG("ohtoken: OhTokenRegistry.sAndroidToOh not reachable\n");
    return;
  }
  t.mapKeySet = env->GetMethodID(map, "keySet", "()Ljava/util/Set;");
  t.mapPut = env->GetMethodID(map, "put",
                              "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;");
  t.mapGet = env->GetMethodID(map, "get", "(Ljava/lang/Object;)Ljava/lang/Object;");
  t.setToArray = env->GetMethodID(set, "toArray", "()[Ljava/lang/Object;");
  jmethodID valueOf = env->GetStaticMethodID(longCls, "valueOf", "(J)Ljava/lang/Long;");
  jobject zeroLocal = (valueOf != nullptr)
      ? env->CallStaticObjectMethod(longCls, valueOf, static_cast<jlong>(0))
      : nullptr;
  if (env->ExceptionCheck()) env->ExceptionClear();
  if (zeroLocal != nullptr) {
    t.zero = env->NewGlobalRef(zeroLocal);
    env->DeleteLocalRef(zeroLocal);
  }
  env->DeleteLocalRef(map);
  env->DeleteLocalRef(set);
  env->DeleteLocalRef(longCls);
  t.ok = t.mapKeySet != nullptr && t.mapPut != nullptr && t.mapGet != nullptr &&
         t.setToArray != nullptr && t.zero != nullptr;
  g_tz = t;
  WL_LOG("ohtoken: zeroing %s\n", t.ok ? "ready" : "UNAVAILABLE");
}

bool g_tz_reported = false;

void ZeroOhTokens(JNIEnv* env) {
  if (!g_tz.ok) return;
  jobject map = env->GetStaticObjectField(g_tz.registry, g_tz.androidToOh);
  if (map == nullptr) return;
  jobject keys = env->CallObjectMethod(map, g_tz.mapKeySet);
  if (env->ExceptionCheck() || keys == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(map);
    return;
  }
  jobjectArray arr = static_cast<jobjectArray>(env->CallObjectMethod(keys, g_tz.setToArray));
  env->DeleteLocalRef(keys);
  if (env->ExceptionCheck() || arr == nullptr) {
    env->ExceptionClear();
    env->DeleteLocalRef(map);
    return;
  }
  jsize n = env->GetArrayLength(arr);
  int zeroed = 0;
  for (jsize i = 0; i < n; i++) {
    jobject key = env->GetObjectArrayElement(arr, i);
    if (key == nullptr) continue;
    jobject cur = env->CallObjectMethod(map, g_tz.mapGet, key);
    if (!env->ExceptionCheck() && cur != nullptr && !env->IsSameObject(cur, g_tz.zero)) {
      env->CallObjectMethod(map, g_tz.mapPut, key, g_tz.zero);
      if (env->ExceptionCheck()) env->ExceptionClear();
      else zeroed++;
    }
    if (env->ExceptionCheck()) env->ExceptionClear();
    if (cur != nullptr) env->DeleteLocalRef(cur);
    env->DeleteLocalRef(key);
  }
  env->DeleteLocalRef(arr);
  env->DeleteLocalRef(map);
  if (zeroed != 0 && !g_tz_reported) {
    g_tz_reported = true;
    WL_LOG("ohtoken: zeroed %d OH ability token mapping(s) [NOTE: token is not why "
           "CreateWindow fails]\n", zeroed);
  }
}

// ------------------------------------------------ main-window reuse (the real fix)
//
// This board has NO legacy WindowManagerService.  SA 4606 is served by the
// SceneBoard stack, which answers the OHOS.ISceneSessionManager interface token,
// while the adapter's createSession writes OHOS.IWindowManager and calls the legacy
// CreateWindow.  The stub rejects the transaction (handle:3 error:1) -> WMError 1005
// -> addToDisplay returns -9 -> InvalidDisplayException kills the app.  Nothing about
// the ability token, the window property or the surface node changes that: there is
// simply no server on the other end of that interface.  (libwms.z.so does not exist
// anywhere on /system or /vendor; foundation has libscene_session/libsession_manager
// mapped instead.  Board is OpenHarmony 6.1.0.31; the adapter's legacy path was
// validated on a 7.0.0.18 image that still shipped libwms.)
//
// WindowSessionAdapter.addToDisplay already has the escape hatch: if
// OhTokenRegistry.getMainSessionId(attrs.token) > 0 it reuses the OH main
// SceneSession that SCB created for the ability and skips CreateAndConnect
// entirely.  The adapter's own comment says the capture wiring "awaits an OH-side
// mechanism", so getMainSessionId always returns -1 and it always falls through to
// the dead legacy call.  We supply the id ourselves -- addToDisplay then returns
// ADD_FLAG_APP_VISIBLE and the app stops dying.  relayout only uses the id as a
// key into the surface bridge, so it does not have to be SCB's real persistentId.
struct MainSessionRefs {
  jmethodID setMainSessionId = nullptr;  // static (long ohTokenAddr, int persistentId)
  jmethodID mapValues = nullptr;
  jmethodID collToArray = nullptr;
  jmethodID longValue = nullptr;
  bool ok = false;
};

MainSessionRefs g_ms;
bool g_ms_reported = false;

void InitMainSessionRefs(JNIEnv* env) {
  if (g_tz.registry == nullptr) return;  // shares OhTokenRegistry plumbing
  MainSessionRefs m;
  m.setMainSessionId = env->GetStaticMethodID(g_tz.registry, "setMainSessionId", "(JI)V");
  jclass map = env->FindClass("java/util/Map");
  jclass coll = env->FindClass("java/util/Collection");
  jclass longCls = env->FindClass("java/lang/Long");
  if (m.setMainSessionId == nullptr || map == nullptr || coll == nullptr ||
      longCls == nullptr) {
    env->ExceptionClear();
    WL_LOG("mainwin: OhTokenRegistry.setMainSessionId not reachable\n");
    return;
  }
  m.mapValues = env->GetMethodID(map, "values", "()Ljava/util/Collection;");
  m.collToArray = env->GetMethodID(coll, "toArray", "()[Ljava/lang/Object;");
  m.longValue = env->GetMethodID(longCls, "longValue", "()J");
  env->DeleteLocalRef(map);
  env->DeleteLocalRef(coll);
  env->DeleteLocalRef(longCls);
  m.ok = m.mapValues != nullptr && m.collToArray != nullptr && m.longValue != nullptr;
  g_ms = m;
  WL_LOG("mainwin: reuse-injection %s\n", m.ok ? "ready" : "UNAVAILABLE");
}

// The id only has to be > 0 and stable.  Override with WL_MAIN_SESSION_ID once we
// can read SCB's real persistentId for the ability.
int MainSessionId() {
  const char* s = getenv("WL_MAIN_SESSION_ID");
  int v = (s != nullptr) ? atoi(s) : 0;
  return v > 0 ? v : 1;
}

void InjectMainSession(JNIEnv* env) {
  if (!g_ms.ok || !g_tz.ok) return;
  jobject map = env->GetStaticObjectField(g_tz.registry, g_tz.androidToOh);
  if (map == nullptr) return;
  jobject vals = env->CallObjectMethod(map, g_ms.mapValues);
  env->DeleteLocalRef(map);
  if (env->ExceptionCheck() || vals == nullptr) {
    env->ExceptionClear();
    return;
  }
  jobjectArray arr = static_cast<jobjectArray>(env->CallObjectMethod(vals, g_ms.collToArray));
  env->DeleteLocalRef(vals);
  if (env->ExceptionCheck() || arr == nullptr) {
    env->ExceptionClear();
    return;
  }
  const int id = MainSessionId();
  jsize n = env->GetArrayLength(arr);
  int done = 0;
  for (jsize i = 0; i < n; i++) {
    jobject v = env->GetObjectArrayElement(arr, i);
    if (v == nullptr) continue;
    jlong addr = env->CallLongMethod(v, g_ms.longValue);
    if (!env->ExceptionCheck() && addr != 0) {
      // setMainSessionId reverses addr through sOhToAndroid, so it only takes
      // effect once ScheduleLaunchAbility has registered the ability token.
      env->CallStaticVoidMethod(g_tz.registry, g_ms.setMainSessionId, addr,
                                static_cast<jint>(id));
      if (env->ExceptionCheck()) env->ExceptionClear();
      else done++;
    }
    if (env->ExceptionCheck()) env->ExceptionClear();
    env->DeleteLocalRef(v);
  }
  env->DeleteLocalRef(arr);
  if (done != 0 && !g_ms_reported) {
    g_ms_reported = true;
    WL_LOG("mainwin: pointed %d ability token(s) at OH main session id=%d; addToDisplay "
           "will reuse instead of calling the missing legacy WMS\n", done, id);
  }
}

void* BridgeInitThread(void*) {
  JNIEnv* env = nullptr;
  JavaVMAttachArgs args = {JNI_VERSION_1_6, "wl-bridge-init", nullptr};
  for (int attempt = 0; attempt < 600; attempt++) {
    if (g_theme.vm->AttachCurrentThreadAsDaemon(&env, &args) == JNI_OK && env != nullptr) break;
    env = nullptr;
    usleep(20 * 1000);
  }
  if (env == nullptr) {
    WL_LOG("bridge: could not attach the bridge-init thread\n");
    return nullptr;
  }
  InitAdapterBridge(env);
  InstallAdapterStubs(env);  // the bridge's registrars rebind connectAbility; retake it
  WL_LOG("bridge: init thread done\n");
  g_theme.vm->DetachCurrentThread();
  return nullptr;
}

void StartBridgeInit() {
  if (getenv("WL_NO_BRIDGE_INIT") != nullptr) {
    WL_LOG("bridge: disabled by WL_NO_BRIDGE_INIT\n");
    return;
  }
  pthread_t t;
  if (pthread_create(&t, nullptr, BridgeInitThread, nullptr) != 0) {
    WL_LOG("bridge: pthread_create failed\n");
    return;
  }
  pthread_detach(t);
}

// Write the runtime class name of `obj` into buf.  Best effort: on any failure buf is
// left as "?" so callers never have to null-check.
void ClassNameOf(JNIEnv* env, jobject obj, char* buf, size_t n) {
  snprintf(buf, n, "?");
  if (obj == nullptr) { snprintf(buf, n, "null"); return; }
  jclass c = env->GetObjectClass(obj);
  if (c == nullptr) { env->ExceptionClear(); return; }
  jclass clsCls = env->FindClass("java/lang/Class");
  jmethodID getName = clsCls != nullptr
      ? env->GetMethodID(clsCls, "getName", "()Ljava/lang/String;") : nullptr;
  if (getName != nullptr) {
    jstring s = static_cast<jstring>(env->CallObjectMethod(c, getName));
    if (env->ExceptionCheck()) env->ExceptionClear();
    if (s != nullptr) {
      const char* p = env->GetStringUTFChars(s, nullptr);
      if (p != nullptr) { snprintf(buf, n, "%s", p); env->ReleaseStringUTFChars(s, p); }
      env->DeleteLocalRef(s);
    }
  }
  if (clsCls != nullptr) env->DeleteLocalRef(clsCls);
  env->DeleteLocalRef(c);
}

// Walk the main Looper's MessageQueue and log everything sitting in it.
//
// Why this probe exists.  ViewRootImpl.setView() calls requestLayout() ->
// scheduleTraversals(), which installs a SYNC BARRIER on the main queue
// (MessageQueue.postSyncBarrier) and only removes it inside doTraversal() -- which runs
// from a Choreographer frame callback, i.e. only once a vsync arrives.  On this board
// nothing drives vsync, so the suspicion is that the barrier is never lifted.  A barrier
// blocks every *synchronous* message behind it forever while the looper keeps happily
// running, so the symptom is a main thread parked in nativePollOnce with a full queue --
// which looks exactly like a hang, and is exactly what we see (the adapter's
// "dispatchByActivityToken posted to main Looper: RESUMED" runnable never runs, so
// AbilityTransitionDone never fires and AMS eventually kills the ability on
// LIFECYCLE_TIMEOUT).
//
// A barrier is a Message with target == null.  Async messages (flags & 1) are the ones
// allowed to run past it -- Choreographer's own frame message is async for this reason.
void DumpMainQueue(JNIEnv* env) {
  jclass looperCls = env->FindClass("android/os/Looper");
  if (looperCls == nullptr) { env->ExceptionClear(); return; }
  jmethodID getMain = env->GetStaticMethodID(looperCls, "getMainLooper", "()Landroid/os/Looper;");
  if (getMain == nullptr) { env->ExceptionClear(); env->DeleteLocalRef(looperCls); return; }
  jobject looper = env->CallStaticObjectMethod(looperCls, getMain);
  if (env->ExceptionCheck()) env->ExceptionClear();
  if (looper == nullptr) { env->DeleteLocalRef(looperCls); return; }

  jfieldID qField = env->GetFieldID(looperCls, "mQueue", "Landroid/os/MessageQueue;");
  if (qField == nullptr) env->ExceptionClear();
  jobject queue = qField != nullptr ? env->GetObjectField(looper, qField) : nullptr;
  env->DeleteLocalRef(looper);
  env->DeleteLocalRef(looperCls);
  if (queue == nullptr) return;

  jclass mqCls = env->GetObjectClass(queue);
  jfieldID headField = env->GetFieldID(mqCls, "mMessages", "Landroid/os/Message;");
  if (headField == nullptr) env->ExceptionClear();
  jobject msg = headField != nullptr ? env->GetObjectField(queue, headField) : nullptr;
  env->DeleteLocalRef(mqCls);
  env->DeleteLocalRef(queue);

  jclass msgCls = env->FindClass("android/os/Message");
  if (msgCls == nullptr) { env->ExceptionClear(); if (msg) env->DeleteLocalRef(msg); return; }
  jfieldID fTarget = env->GetFieldID(msgCls, "target", "Landroid/os/Handler;");
  jfieldID fNext   = env->GetFieldID(msgCls, "next", "Landroid/os/Message;");
  jfieldID fWhat   = env->GetFieldID(msgCls, "what", "I");
  jfieldID fFlags  = env->GetFieldID(msgCls, "flags", "I");
  jfieldID fCb     = env->GetFieldID(msgCls, "callback", "Ljava/lang/Runnable;");
  if (env->ExceptionCheck()) env->ExceptionClear();

  if (msg == nullptr) {
    WL_LOG("mq: main queue is EMPTY (no barrier, nothing pending)\n");
    env->DeleteLocalRef(msgCls);
    return;
  }

  int barriers = 0;
  int i = 0;
  for (; msg != nullptr && i < 24; i++) {
    jobject target = fTarget != nullptr ? env->GetObjectField(msg, fTarget) : nullptr;
    jobject cb     = fCb != nullptr ? env->GetObjectField(msg, fCb) : nullptr;
    jint what      = fWhat != nullptr ? env->GetIntField(msg, fWhat) : -1;
    jint flags     = fFlags != nullptr ? env->GetIntField(msg, fFlags) : 0;
    char tn[128], cn[128];
    ClassNameOf(env, target, tn, sizeof(tn));
    ClassNameOf(env, cb, cn, sizeof(cn));
    if (target == nullptr) barriers++;
    WL_LOG("mq: [%d] %s what=%d async=%d handler=%s callback=%s\n", i,
           target == nullptr ? "SYNC-BARRIER" : "msg", what, (flags & 1) ? 1 : 0, tn, cn);
    if (target != nullptr) env->DeleteLocalRef(target);
    if (cb != nullptr) env->DeleteLocalRef(cb);
    jobject next = fNext != nullptr ? env->GetObjectField(msg, fNext) : nullptr;
    env->DeleteLocalRef(msg);
    msg = next;
  }
  if (msg != nullptr) env->DeleteLocalRef(msg);
  env->DeleteLocalRef(msgCls);
  WL_LOG("mq: walked %d entries, %d sync-barrier(s) at/near the head\n", i, barriers);
}

// ------------------------------------------------------- thread PC sampler
//
// The OH vsync callback thread ("DER-vsync-oh", created inside
// android_view_DisplayEventReceiver.cpp's ensureAttachedForVsync) burns ~100% of a
// core and never lets Choreographer post a frame, so the traversal sync barrier is
// never lifted and the ability is killed on LIFECYCLE_TIMEOUT.  /proc/<tid>/syscall
// says "running" on every sample, i.e. it is spinning in USER space -- so the only
// thing that identifies the loop is the program counter.
//
// dumpcatcher cannot get it ("normal stack: failed to fully dump due to timeout")
// and SIGQUIT produces no ART thread dump on this substrate, so sample it ourselves:
// tgkill the thread with SIGPROF, snapshot pc/lr/fp/sp out of the ucontext, and
// resolve each frame with dladdr.  The handler only stores integers -- no
// allocation, no logging -- so it stays async-signal-safe; the frame walk and the
// logging happen back on the sampler thread.
struct PcSample {
  volatile uintptr_t pc = 0;
  volatile uintptr_t lr = 0;
  volatile uintptr_t fp = 0;
  volatile uintptr_t sp = 0;
  volatile int ready = 0;
};
PcSample g_pc_sample;

void PcSampleHandler(int, siginfo_t*, void* ctx) {
  auto* uc = static_cast<ucontext_t*>(ctx);
  g_pc_sample.pc = static_cast<uintptr_t>(uc->uc_mcontext.pc);
  g_pc_sample.lr = static_cast<uintptr_t>(uc->uc_mcontext.regs[30]);
  g_pc_sample.fp = static_cast<uintptr_t>(uc->uc_mcontext.regs[29]);
  g_pc_sample.sp = static_cast<uintptr_t>(uc->uc_mcontext.sp);
  __atomic_store_n(&g_pc_sample.ready, 1, __ATOMIC_RELEASE);
}

// Returns the tid of the first thread in this process whose comm matches `name`,
// or 0.  comm is capped at 15 chars by the kernel, so match on a prefix.
int FindThreadByComm(const char* name) {
  DIR* d = opendir("/proc/self/task");
  if (d == nullptr) return 0;
  const size_t want = strlen(name) > 15 ? 15 : strlen(name);
  int found = 0;
  for (struct dirent* e = readdir(d); e != nullptr && found == 0; e = readdir(d)) {
    if (e->d_name[0] < '0' || e->d_name[0] > '9') continue;
    char path[128];
    snprintf(path, sizeof(path), "/proc/self/task/%s/comm", e->d_name);
    FILE* f = fopen(path, "r");
    if (f == nullptr) continue;
    char comm[64] = {0};
    if (fgets(comm, sizeof(comm), f) != nullptr) {
      char* nl = strchr(comm, '\n');
      if (nl != nullptr) *nl = '\0';
      if (strncmp(comm, name, want) == 0) found = atoi(e->d_name);
    }
    fclose(f);
  }
  closedir(d);
  return found;
}

void LogFrame(const char* label, uintptr_t addr) {
  if (addr == 0) { WL_LOG("pcsample:   %s = 0\n", label); return; }
  Dl_info info;
  memset(&info, 0, sizeof(info));
  if (dladdr(reinterpret_cast<void*>(addr), &info) != 0 && info.dli_fname != nullptr) {
    const char* base = strrchr(info.dli_fname, '/');
    base = base != nullptr ? base + 1 : info.dli_fname;
    uintptr_t off = addr - reinterpret_cast<uintptr_t>(info.dli_fbase);
    if (info.dli_sname != nullptr) {
      WL_LOG("pcsample:   %s = %s+0x%lx  (%s)\n", label, base,
             static_cast<unsigned long>(off), info.dli_sname);
    } else {
      WL_LOG("pcsample:   %s = %s+0x%lx\n", label, base, static_cast<unsigned long>(off));
    }
  } else {
    WL_LOG("pcsample:   %s = 0x%lx (unmapped/anon -- JIT?)\n", label,
           static_cast<unsigned long>(addr));
  }
}

// Walk the arm64 frame-pointer chain from OUTSIDE the handler.  The target thread is
// alive so its stack is still mapped and readable from here; the guards below (16-byte
// alignment, strictly increasing, stays inside 1 MB of the sampled sp) keep a garbage
// fp from walking us off into an unmapped page.
void WalkFrames(uintptr_t fp, uintptr_t sp) {
  const uintptr_t lo = sp;
  const uintptr_t hi = sp + (1u << 20);
  uintptr_t cur = fp;
  for (int depth = 0; depth < 12; depth++) {
    if (cur == 0 || (cur & 0xf) != 0 || cur < lo || cur + 16 > hi) break;
    auto* frame = reinterpret_cast<uintptr_t*>(cur);
    uintptr_t next = frame[0];
    uintptr_t ret = frame[1];
    if (ret == 0) break;
    char label[24];
    snprintf(label, sizeof(label), "#%d", depth + 1);
    LogFrame(label, ret);
    if (next <= cur) break;
    cur = next;
  }
}

// Sample `name` `rounds` times.  Installs the SIGPROF handler once; SIGPROF is unused
// by ART and by the OH runtime, and the default action would kill the process, so the
// handler must be in place before the first tgkill.
void SampleThread(const char* name, int rounds) {
  static bool installed = false;
  if (!installed) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = PcSampleHandler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGPROF, &sa, nullptr) != 0) {
      WL_LOG("pcsample: sigaction(SIGPROF) failed errno=%d\n", errno);
      return;
    }
    installed = true;
  }
  int tid = FindThreadByComm(name);
  if (tid == 0) { WL_LOG("pcsample: no thread named %s\n", name); return; }
  WL_LOG("pcsample: === %s tid=%d, %d rounds ===\n", name, tid, rounds);
  for (int r = 0; r < rounds; r++) {
    __atomic_store_n(&g_pc_sample.ready, 0, __ATOMIC_RELEASE);
    if (syscall(SYS_tgkill, getpid(), tid, SIGPROF) != 0) {
      WL_LOG("pcsample: tgkill tid=%d failed errno=%d\n", tid, errno);
      return;
    }
    int spins = 0;
    while (__atomic_load_n(&g_pc_sample.ready, __ATOMIC_ACQUIRE) == 0 && spins < 2000) {
      usleep(500);
      spins++;
    }
    if (__atomic_load_n(&g_pc_sample.ready, __ATOMIC_ACQUIRE) == 0) {
      WL_LOG("pcsample: round %d timed out -- thread never ran the handler\n", r);
      return;
    }
    WL_LOG("pcsample: round %d sp=0x%lx\n", r, static_cast<unsigned long>(g_pc_sample.sp));
    LogFrame("pc", g_pc_sample.pc);
    LogFrame("lr", g_pc_sample.lr);
    WalkFrames(g_pc_sample.fp, g_pc_sample.sp);
    usleep(150 * 1000);
  }
}

// ---------------------------------------------------------------------------
// Render-path probe.
//
// By this point the window is genuinely up: measure and layout both succeed
// (decor 1200x1920, every child laid out, the real Noice view tree with its
// Toolbar/"声音库" title and FragmentContainerView), mViewVisibility=0,
// mAppVisible=true, and ViewRootImpl reports mLastPerformDrawSkippedReason=null
// and mLastPerformTraversalsSkipDrawReason=null -- i.e. it does NOT think it
// skipped drawing.  Yet the surface stays blank and /proc/<pid>/task shows
// RenderThread with u=0 s=0: it was created and has never run.  mDirty also
// stays Rect(0,0-1200,1920), and ViewRootImpl.draw() empties mDirty on the way
// into the hardware branch -- so that branch is not being taken.
//
// Everything that decides between the two branches lives on
// ViewRootImpl.mAttachInfo (mThreadedRenderer, mHardwareAccelerated) and on the
// renderer object itself (mEnabled / mRequested / mInitialized / mNativeProxy).
// The substrate logs none of it, so read it directly.  mRoots comes from
// WindowManagerGlobal, which is where ViewRootImpl instances are registered.
void DumpObjectFields(JNIEnv* env, jobject obj, const char* label, int maxVal) {
  if (obj == nullptr) { WL_LOG("rp: %s = null\n", label); return; }
  char cn[128];
  ClassNameOf(env, obj, cn, sizeof(cn));
  jclass classCls = env->FindClass("java/lang/Class");
  jclass fieldCls = env->FindClass("java/lang/reflect/Field");
  jclass strCls = env->FindClass("java/lang/String");
  if (classCls == nullptr || fieldCls == nullptr || strCls == nullptr) {
    env->ExceptionClear();
    WL_LOG("rp: %s (%s): no reflection classes\n", label, cn);
    return;
  }
  jmethodID getFields = env->GetMethodID(classCls, "getDeclaredFields",
                                         "()[Ljava/lang/reflect/Field;");
  jmethodID getName = env->GetMethodID(fieldCls, "getName", "()Ljava/lang/String;");
  jmethodID setAcc = env->GetMethodID(fieldCls, "setAccessible", "(Z)V");
  jmethodID fGet = env->GetMethodID(fieldCls, "get",
                                    "(Ljava/lang/Object;)Ljava/lang/Object;");
  jmethodID valueOf = env->GetStaticMethodID(strCls, "valueOf",
                                             "(Ljava/lang/Object;)Ljava/lang/String;");
  if (getFields == nullptr || getName == nullptr || setAcc == nullptr ||
      fGet == nullptr || valueOf == nullptr) {
    env->ExceptionClear();
    WL_LOG("rp: %s (%s): no reflection methods\n", label, cn);
    return;
  }
  jclass cls = env->GetObjectClass(obj);
  auto* arr = static_cast<jobjectArray>(env->CallObjectMethod(cls, getFields));
  if (env->ExceptionCheck()) { env->ExceptionClear(); arr = nullptr; }
  env->DeleteLocalRef(cls);
  if (arr == nullptr) { WL_LOG("rp: %s (%s): getDeclaredFields failed\n", label, cn); return; }

  jsize n = env->GetArrayLength(arr);
  WL_LOG("rp: %s (%s) %d field(s):\n", label, cn, static_cast<int>(n));
  for (jsize i = 0; i < n; i++) {
    jobject f = env->GetObjectArrayElement(arr, i);
    if (f == nullptr) continue;
    env->CallVoidMethod(f, setAcc, JNI_TRUE);
    if (env->ExceptionCheck()) env->ExceptionClear();
    auto nameStr = static_cast<jstring>(env->CallObjectMethod(f, getName));
    if (env->ExceptionCheck()) { env->ExceptionClear(); nameStr = nullptr; }
    jobject val = env->CallObjectMethod(f, fGet, obj);
    if (env->ExceptionCheck()) { env->ExceptionClear(); val = nullptr; }
    auto valStr = static_cast<jstring>(env->CallStaticObjectMethod(strCls, valueOf, val));
    if (env->ExceptionCheck()) { env->ExceptionClear(); valStr = nullptr; }
    const char* nu = nameStr != nullptr ? env->GetStringUTFChars(nameStr, nullptr) : nullptr;
    const char* vu = valStr != nullptr ? env->GetStringUTFChars(valStr, nullptr) : nullptr;
    // Configuration/Rect toString runs to hundreds of characters and drowns the
    // handful of booleans this probe exists for, so clamp every value.
    char vb[192];
    if (vu != nullptr) {
      int lim = maxVal > 0 && maxVal < static_cast<int>(sizeof(vb)) ? maxVal
                                                                    : static_cast<int>(sizeof(vb)) - 1;
      snprintf(vb, sizeof(vb), "%.*s", lim, vu);
    } else {
      snprintf(vb, sizeof(vb), "<unreadable>");
    }
    WL_LOG("rp:    %s = %s\n", nu != nullptr ? nu : "?", vb);
    if (nu != nullptr) env->ReleaseStringUTFChars(nameStr, nu);
    if (vu != nullptr) env->ReleaseStringUTFChars(valStr, vu);
    if (nameStr != nullptr) env->DeleteLocalRef(nameStr);
    if (valStr != nullptr) env->DeleteLocalRef(valStr);
    if (val != nullptr) env->DeleteLocalRef(val);
    env->DeleteLocalRef(f);
  }
  env->DeleteLocalRef(arr);
}

// The OH side of the surface bridge logs everything through HiLogPrint(LOG_CORE),
// and hilogd drops LOG_CORE writes from app-uid processes -- so none of
// getOhNativeWindow's own diagnostics are readable from here.  Both entry points are
// extern "C" with default visibility though, so call them directly and see for
// ourselves whether the OH RSSurfaceNode ever yields a usable ANativeWindow.
void ProbeOhSurfaceBridge() {
  using FnGetLast = int32_t (*)();
  using FnGetNw = void* (*)(int32_t);
  auto getLast = reinterpret_cast<FnGetLast>(dlsym(RTLD_DEFAULT, "oh_wm_get_last_session"));
  auto getNw = reinterpret_cast<FnGetNw>(dlsym(RTLD_DEFAULT, "oh_wm_get_native_window"));
  if (getLast == nullptr || getNw == nullptr) {
    WL_LOG("rp: oh surface bridge not exported (get_last=%p get_nw=%p)\n",
           reinterpret_cast<void*>(getLast), reinterpret_cast<void*>(getNw));
    return;
  }
  int32_t sid = getLast();
  void* nw = getNw(sid);
  WL_LOG("rp: oh_wm_get_last_session=%d -> oh_wm_get_native_window(%d)=%p\n", sid, sid, nw);
  // Session ids start at 1; if the "last touched session" hint never got set the
  // lookup above is asking about session 0 and is meaningless, so try 1 as well.
  if (sid != 1) WL_LOG("rp: oh_wm_get_native_window(1)=%p\n", getNw(1));
}

void DumpRenderPath(JNIEnv* env) {
  ProbeOhSurfaceBridge();
  jclass wmgCls = env->FindClass("android/view/WindowManagerGlobal");
  if (wmgCls == nullptr) { env->ExceptionClear(); WL_LOG("rp: no WindowManagerGlobal\n"); return; }
  jmethodID getInst = env->GetStaticMethodID(wmgCls, "getInstance",
                                             "()Landroid/view/WindowManagerGlobal;");
  if (getInst == nullptr) { env->ExceptionClear(); env->DeleteLocalRef(wmgCls); return; }
  jobject wmg = env->CallStaticObjectMethod(wmgCls, getInst);
  if (env->ExceptionCheck()) env->ExceptionClear();
  env->DeleteLocalRef(wmgCls);
  if (wmg == nullptr) { WL_LOG("rp: WindowManagerGlobal.getInstance() = null\n"); return; }

  jobject roots = GetObjField(env, wmg, "mRoots", "Ljava/util/ArrayList;");
  env->DeleteLocalRef(wmg);
  if (roots == nullptr) { WL_LOG("rp: mRoots not reachable\n"); return; }
  jclass listCls = env->FindClass("java/util/ArrayList");
  jmethodID sizeM = env->GetMethodID(listCls, "size", "()I");
  jmethodID getM = env->GetMethodID(listCls, "get", "(I)Ljava/lang/Object;");
  jint count = env->CallIntMethod(roots, sizeM);
  if (env->ExceptionCheck()) { env->ExceptionClear(); count = 0; }
  WL_LOG("rp: --- WindowManagerGlobal.mRoots has %d ViewRootImpl(s) ---\n",
         static_cast<int>(count));
  for (jint i = 0; i < count && i < 2; i++) {
    jobject vr = env->CallObjectMethod(roots, getM, i);
    if (env->ExceptionCheck()) { env->ExceptionClear(); continue; }
    if (vr == nullptr) continue;

    jobject ai = GetObjField(env, vr, "mAttachInfo", "Landroid/view/View$AttachInfo;");
    if (ai == nullptr) {
      WL_LOG("rp: root[%d] mAttachInfo = null\n", static_cast<int>(i));
    } else {
      jclass aiCls = env->GetObjectClass(ai);
      jfieldID hwF = env->GetFieldID(aiCls, "mHardwareAccelerated", "Z");
      if (hwF == nullptr) env->ExceptionClear();
      jfieldID hwrF = env->GetFieldID(aiCls, "mHardwareAccelerationRequested", "Z");
      if (hwrF == nullptr) env->ExceptionClear();
      env->DeleteLocalRef(aiCls);
      WL_LOG("rp: root[%d] AttachInfo mHardwareAccelerated=%d mHardwareAccelerationRequested=%d\n",
             static_cast<int>(i),
             hwF != nullptr ? env->GetBooleanField(ai, hwF) : -1,
             hwrF != nullptr ? env->GetBooleanField(ai, hwrF) : -1);
      // Field type is ThreadedRenderer on some builds, HardwareRenderer on others.
      jobject tr = GetObjField(env, ai, "mThreadedRenderer",
                               "Landroid/view/ThreadedRenderer;");
      if (tr == nullptr) {
        tr = GetObjField(env, ai, "mThreadedRenderer",
                         "Landroid/graphics/HardwareRenderer;");
      }
      DumpObjectFields(env, tr, "AttachInfo.mThreadedRenderer", 96);
      if (tr != nullptr) env->DeleteLocalRef(tr);
      env->DeleteLocalRef(ai);
    }

    jclass vrCls = env->GetObjectClass(vr);
    jfieldID blastF = env->GetFieldID(vrCls, "mUseBLASTAdapter", "Z");
    if (blastF == nullptr) env->ExceptionClear();
    jfieldID noBlastF = env->GetFieldID(vrCls, "mForceDisableBLAST", "Z");
    if (noBlastF == nullptr) env->ExceptionClear();
    env->DeleteLocalRef(vrCls);
    WL_LOG("rp: root[%d] mUseBLASTAdapter=%d mForceDisableBLAST=%d\n", static_cast<int>(i),
           blastF != nullptr ? env->GetBooleanField(vr, blastF) : -1,
           noBlastF != nullptr ? env->GetBooleanField(vr, noBlastF) : -1);

    jobject sc = GetObjField(env, vr, "mSurfaceControl", "Landroid/view/SurfaceControl;");
    if (sc == nullptr) {
      WL_LOG("rp: root[%d] mSurfaceControl = null\n", static_cast<int>(i));
    } else {
      jclass scCls = env->GetObjectClass(sc);
      jmethodID scValid = env->GetMethodID(scCls, "isValid", "()Z");
      if (scValid == nullptr) env->ExceptionClear();
      jfieldID scNat = env->GetFieldID(scCls, "mNativeObject", "J");
      if (scNat == nullptr) env->ExceptionClear();
      jboolean v = scValid != nullptr ? env->CallBooleanMethod(sc, scValid) : JNI_FALSE;
      if (env->ExceptionCheck()) env->ExceptionClear();
      WL_LOG("rp: root[%d] mSurfaceControl isValid=%d mNativeObject=0x%llx\n",
             static_cast<int>(i), static_cast<int>(v),
             scNat != nullptr ? static_cast<unsigned long long>(env->GetLongField(sc, scNat))
                              : 0ULL);
      env->DeleteLocalRef(scCls);
      env->DeleteLocalRef(sc);
    }

    jobject bbq = GetObjField(env, vr, "mBlastBufferQueue",
                              "Landroid/graphics/BLASTBufferQueue;");
    if (bbq == nullptr) {
      WL_LOG("rp: root[%d] mBlastBufferQueue = null\n", static_cast<int>(i));
    } else {
      char bn[128];
      ClassNameOf(env, bbq, bn, sizeof(bn));
      WL_LOG("rp: root[%d] mBlastBufferQueue = %s\n", static_cast<int>(i), bn);
      env->DeleteLocalRef(bbq);
    }

    jobject surf = GetObjField(env, vr, "mSurface", "Landroid/view/Surface;");
    if (surf == nullptr) {
      WL_LOG("rp: root[%d] mSurface = null\n", static_cast<int>(i));
    } else {
      jclass sCls = env->GetObjectClass(surf);
      jmethodID isValid = env->GetMethodID(sCls, "isValid", "()Z");
      if (isValid == nullptr) env->ExceptionClear();
      jfieldID natF = env->GetFieldID(sCls, "mNativeObject", "J");
      if (natF == nullptr) env->ExceptionClear();
      jboolean valid = isValid != nullptr ? env->CallBooleanMethod(surf, isValid) : JNI_FALSE;
      if (env->ExceptionCheck()) env->ExceptionClear();
      WL_LOG("rp: root[%d] mSurface isValid=%d mNativeObject=0x%llx\n", static_cast<int>(i),
             static_cast<int>(valid),
             natF != nullptr
                 ? static_cast<unsigned long long>(env->GetLongField(surf, natF))
                 : 0ULL);
      env->DeleteLocalRef(sCls);
      env->DeleteLocalRef(surf);
    }
    env->DeleteLocalRef(vr);
  }
  env->DeleteLocalRef(listCls);
  env->DeleteLocalRef(roots);
}

// WL_FORCE_BLAST -- hand ViewRootImpl a Surface that actually has a buffer behind it.
//
// ViewRootImpl.relayoutWindow picks one of two ways to fill mSurface:
//
//   !useBLAST()  ->  mSurface.copyFrom(mSurfaceControl)
//   useBLAST()   ->  mSurface.transferFrom(getOrCreateBLASTSurface())
//
// copyFrom bottoms out in SurfaceControl::getSurface(), which needs a real
// SurfaceFlinger to hand back an IGraphicBufferProducer.  This board has none, so
// it returns null and mSurface.mNativeObject stays 0 -- which is exactly what the
// probe above measures.  An empty Surface makes ThreadedRenderer.initialize() fail
// (mInitialized/mEnabled stay false, RenderThread never accumulates any CPU), and
// the software fallback's lockCanvas() fails on it too, so mDirty is never cleared
// and the window composites blank.
//
// The BLAST route is the one this substrate is actually built for:
// WindowSessionAdapter stamps the session id onto the SurfaceControl so
// BBQ_nativeGetSurface can resolve it to the OH RSSurfaceNode and return a real
// OHNativeWindow*.  It is gated on ADD_FLAG_USE_BLAST, which buildAddDisplayFlags
// deliberately does not set -- reverted 2026-05-08 (G2.14ag) because cold start was
// then dying of LIFECYCLE_TIMEOUT before setView.  That blocker was the
// onCreate->onResume gap, which is now fixed (ResumeActivityItem injection + the
// ScopedJniAttachment ABI shim), so the revert's premise no longer holds.
//
// The flag lives in the framework jar, which this board forbids replacing, so flip
// the field it lands in instead.  Returns the number of roots changed.
int ForceBlastAdapter(JNIEnv* env) {
  jclass wmgCls = env->FindClass("android/view/WindowManagerGlobal");
  if (wmgCls == nullptr) { env->ExceptionClear(); return 0; }
  jmethodID getInst = env->GetStaticMethodID(wmgCls, "getInstance",
                                             "()Landroid/view/WindowManagerGlobal;");
  if (getInst == nullptr) { env->ExceptionClear(); env->DeleteLocalRef(wmgCls); return 0; }
  jobject wmg = env->CallStaticObjectMethod(wmgCls, getInst);
  if (env->ExceptionCheck()) env->ExceptionClear();
  env->DeleteLocalRef(wmgCls);
  if (wmg == nullptr) return 0;
  jobject roots = GetObjField(env, wmg, "mRoots", "Ljava/util/ArrayList;");
  env->DeleteLocalRef(wmg);
  if (roots == nullptr) return 0;

  jclass listCls = env->FindClass("java/util/ArrayList");
  jmethodID sizeM = env->GetMethodID(listCls, "size", "()I");
  jmethodID getM = env->GetMethodID(listCls, "get", "(I)Ljava/lang/Object;");
  jint count = env->CallIntMethod(roots, sizeM);
  if (env->ExceptionCheck()) { env->ExceptionClear(); count = 0; }
  int changed = 0;
  for (jint i = 0; i < count; i++) {
    jobject vr = env->CallObjectMethod(roots, getM, i);
    if (env->ExceptionCheck()) { env->ExceptionClear(); continue; }
    if (vr == nullptr) continue;
    jclass vrCls = env->GetObjectClass(vr);
    jfieldID blastF = env->GetFieldID(vrCls, "mUseBLASTAdapter", "Z");
    if (blastF == nullptr) env->ExceptionClear();
    jfieldID noBlastF = env->GetFieldID(vrCls, "mForceDisableBLAST", "Z");
    if (noBlastF == nullptr) env->ExceptionClear();
    // Make the next traversal go all the way through relayoutWindow rather than
    // short-circuiting on "nothing changed" -- otherwise the flag sits unused until
    // something else happens to dirty the window.
    jfieldID forceF = env->GetFieldID(vrCls, "mForceNextWindowRelayout", "Z");
    if (forceF == nullptr) env->ExceptionClear();
    env->DeleteLocalRef(vrCls);
    if (blastF != nullptr && env->GetBooleanField(vr, blastF) == JNI_FALSE) {
      env->SetBooleanField(vr, blastF, JNI_TRUE);
      if (noBlastF != nullptr) env->SetBooleanField(vr, noBlastF, JNI_FALSE);
      if (forceF != nullptr) env->SetBooleanField(vr, forceF, JNI_TRUE);
      changed++;
    }
    env->DeleteLocalRef(vr);
  }
  env->DeleteLocalRef(listCls);
  env->DeleteLocalRef(roots);
  return changed;
}

void* ThemeFixerThread(void*) {
  // Started from a pthread_atfork child handler, so the child's runtime is still doing
  // its own post-fork setup.  ART refuses to attach threads until the runtime is
  // started, so a single attempt always loses the race -- keep retrying instead.
  JNIEnv* env = nullptr;
  JavaVMAttachArgs args = {JNI_VERSION_1_6, "wl-theme-fixer", nullptr};
  for (int attempt = 0; attempt < 600; attempt++) {
    if (g_theme.vm->AttachCurrentThreadAsDaemon(&env, &args) == JNI_OK && env != nullptr) break;
    env = nullptr;
    usleep(20 * 1000);
  }
  if (env == nullptr) {
    WL_LOG("theme: could not attach fixer thread after 12s of retries\n");
    return nullptr;
  }

  jclass atCls = env->FindClass("android/app/ActivityThread");
  jmethodID current = (atCls != nullptr)
      ? env->GetStaticMethodID(atCls, "currentActivityThread", "()Landroid/app/ActivityThread;")
      : nullptr;
  if (current == nullptr) {
    env->ExceptionClear();
    WL_LOG("theme: no ActivityThread.currentActivityThread()\n");
    g_theme.vm->DetachCurrentThread();
    return nullptr;
  }

  InitLaunchQueueRefs(env);
  InstallAdapterStubs(env);
  // The registrars run in the zygote, so their repairs are inherited -- but the child is
  // where java.security first gets touched, so re-probe it here where it matters.
  RepairSecurity(env);
  const bool keepKiller = getenv("WL_KEEP_KILL_HANDLER") != nullptr;
  const bool zeroTokens = getenv("WL_ZERO_OH_TOKEN") != nullptr;
  const bool reuseMain = getenv("WL_NO_MAIN_REUSE") == nullptr;
  const bool g_mq_dump = getenv("WL_NO_MQ_DUMP") == nullptr;
  const bool g_pc_probe = getenv("WL_NO_PC_PROBE") == nullptr;
  const bool g_rp_probe = getenv("WL_NO_RP_PROBE") == nullptr;
  const bool g_force_blast = getenv("WL_FORCE_BLAST") != nullptr;
  int blastFlipped = 0;
  // NOT here: resolving adapter.* classes needs the adapter classloader, which the
  // child is still re-injecting at this point ([INPUT-RT-CL-CHILD]).  Doing a
  // FindClass on adapter/core/OhTokenRegistry from this thread while the main thread
  // is inside AppSpawnXInit.initChild deadlocks on the classloader lock -- the child
  // then sits at "CK_BEFORE_initChild_call" forever with ~104 lines of log.  Both
  // registries are initialised lazily below, once currentActivityThread() proves the
  // main thread is out of initChild and running its looper.
  bool registriesReady = false;
  // On its own thread so that a hang in the substrate's own startup cannot cost us the
  // theme/lifecycle patches, which have to land before the main thread pops the launch.
  if (getenv("WL_NO_BRIDGE_INIT") == nullptr) StartBridgeInit();
  bool announced = false;
  bool announcedLaunch = false;
  // 30 s covers a cold start with room to spare; the thread is a daemon so a miss
  // costs nothing.
  for (int i = 0; i < 30000; i++) {
    jobject at = env->CallStaticObjectMethod(atCls, current);
    if (env->ExceptionCheck()) env->ExceptionClear();
    if (at != nullptr) {
      if (!registriesReady) {
        registriesReady = true;
        InitTokenZeroRefs(env);            // shared plumbing; zeroing stays opt-in
        if (reuseMain) InitMainSessionRefs(env);
      }
      int changed = 0;
      jobject bound = GetObjField(env, at, "mBoundApplication",
                                  "Landroid/app/ActivityThread$AppBindData;");
      if (bound != nullptr) {
        jobject appInfo = GetObjField(env, bound, "appInfo", "Landroid/content/pm/ApplicationInfo;");
        changed += PatchApplicationInfo(env, appInfo);
        if (appInfo != nullptr) env->DeleteLocalRef(appInfo);
        env->DeleteLocalRef(bound);
      }
      jobject app = GetObjField(env, at, "mInitialApplication", "Landroid/app/Application;");
      if (app != nullptr) {
        jobject apk = GetObjField(env, app, "mLoadedApk", "Landroid/app/LoadedApk;");
        if (apk != nullptr) {
          jobject appInfo = GetObjField(env, apk, "mApplicationInfo",
                                        "Landroid/content/pm/ApplicationInfo;");
          changed += PatchApplicationInfo(env, appInfo);
          if (appInfo != nullptr) env->DeleteLocalRef(appInfo);
          env->DeleteLocalRef(apk);
        }
        env->DeleteLocalRef(app);
      }
      if (changed != 0 && !announced) {
        announced = true;
        WL_LOG("theme: forced ApplicationInfo.theme=0x%x className=%s for %s\n", g_theme.theme,
               g_theme.appClass[0] != '\0' ? g_theme.appClass : "(left alone)", g_theme.pkg);
      }
      env->DeleteLocalRef(at);
    }
    if (zeroTokens && (i % 20) == 0) ZeroOhTokens(env);
    // Must land before ViewRootImpl.setView reaches addToDisplay, and the ability
    // token only shows up part-way through startup -- so retry until it takes, then
    // stop: the registry entry persists and hammering JNI here starves the main thread.
    if (reuseMain && !g_ms_reported && (i % 25) == 0) InjectMainSession(env);
    // The substrate installs its killer only once the app runtime is up, and re-installs
    // it on some paths, so keep taking it back rather than clearing it once.
    if (!keepKiller && (i % 20) == 0) DisarmKillHandler(env);
    int launches = PatchPendingLaunches(env);
    if (launches != 0 && !announcedLaunch) {
      announcedLaunch = true;
      WL_LOG("theme: re-themed %d pending launch(es) to 0x%x\n", launches, g_theme.theme);
    }
    // Sample the main queue a handful of times across the startup window.  Set
    // WL_NO_MQ_DUMP to silence it once the question it answers is settled.
    if (g_mq_dump && (i == 8000 || i == 14000 || i == 22000 || i == 29000)) {
      WL_LOG("mq: --- sample at t=%dms after fixer start ---\n", i);
      DumpMainQueue(env);
    }
    // The vsync callback thread is only created once ViewRootImpl has scheduled its
    // first traversal, so there is nothing to sample before the window goes up.
    if (g_pc_probe && (i == 6000 || i == 9000 || i == 12000)) {
      SampleThread("DER-vsync-oh", 4);
    }
    // The renderer is only attached once ViewRootImpl.setView has run, so sample
    // well after the window is up.  Set WL_NO_RP_PROBE to silence it.
    // Must land before ViewRootImpl's first relayoutWindow, and the root only
    // appears part-way through startup, so poll until it takes.
    if (g_force_blast && (i % 10) == 0) {
      int n = ForceBlastAdapter(env);
      if (n != 0) {
        blastFlipped += n;
        WL_LOG("blast: flipped mUseBLASTAdapter=true on %d ViewRootImpl(s) at t=%dms "
               "(total %d)\n", n, i, blastFlipped);
      }
    }
    if (g_rp_probe && (i == 10000 || i == 18000 || i == 26000)) {
      WL_LOG("rp: === render-path sample at t=%dms after fixer start ===\n", i);
      DumpRenderPath(env);
    }
    usleep(1000);
  }
  g_theme.vm->DetachCurrentThread();
  return nullptr;
}

bool g_theme_started = false;

void SpawnThemeFixer() {
  pthread_t t;
  if (pthread_create(&t, nullptr, ThemeFixerThread, nullptr) != 0) {
    WL_LOG("theme: pthread_create failed\n");
    return;
  }
  pthread_detach(t);
  WL_LOG("theme: fixer running for %s -> 0x%x\n", g_theme.pkg, g_theme.theme);
}

// appspawn-x is a zygote: the registrars run once in the daemon and every app inherits
// the bound natives through fork.  Threads are NOT inherited, so a fixer started in the
// daemon dies the moment an app is forked off -- it has to be re-created in the child.
//
// But it must not be created *at* fork.  Right after forking, appspawn-x moves the child
// out of u:r:appspawn:s0 into its HAP domain, and the kernel only permits a process to
// rewrite /proc/self/attr/current while it is single-threaded.  Spawning here makes that
// transition fail with EPERM and appspawn aborts the child outright:
//   "HAP domain transition (via WestLake wrapper) failed rc=-7 errno=1"
//   "applySELinux failed, ret=-7 - aborting child"
// So the child only *arms* here, and the interposed pthread_create below starts the
// fixer once the security context has actually changed -- by then the runtime is
// creating its own threads, so being multi-threaded is no longer a problem.
volatile bool g_in_forked_child = false;
bool g_fixer_spawned = false;
char g_ctx_at_fork[256];

void ReadSelfContext(char* out, size_t n) {
  out[0] = '\0';
  FILE* f = fopen("/proc/self/attr/current", "r");
  if (f == nullptr) return;
  if (fgets(out, static_cast<int>(n), f) == nullptr) out[0] = '\0';
  fclose(f);
}

void RearmThemeFixerAfterFork() {
  if (g_theme.theme == 0) return;
  ReadSelfContext(g_ctx_at_fork, sizeof(g_ctx_at_fork));
  g_fixer_spawned = false;
  g_in_forked_child = true;
}

void MaybeSpawnFixerNow() {
  if (!g_in_forked_child || g_fixer_spawned) return;
  char ctx[256];
  ReadSelfContext(ctx, sizeof(ctx));
  if (ctx[0] == '\0' || strcmp(ctx, g_ctx_at_fork) == 0) return;  // still pre-transition
  g_fixer_spawned = true;  // set first: SpawnThemeFixer re-enters pthread_create
  SpawnThemeFixer();
}

void MaybeStartThemeFixer(JNIEnv* env) {
  if (g_theme_started) return;
  g_theme_started = true;
  if (!ParseThemeOverride(&g_theme)) return;
  if (env->GetJavaVM(&g_theme.vm) != JNI_OK) return;
  // Deliberately NOT spawning here.  This runs inside the zygote's runtime init, and
  // ART requires a zygote to be single-threaded when it forks; an extra attached thread
  // in the daemon risks the spawn path rather than helping it.  Arm only.
  pthread_atfork(nullptr, nullptr, RearmThemeFixerAfterFork);
  WL_LOG("theme: armed for %s -> 0x%x (fires in forked children)\n", g_theme.pkg,
         g_theme.theme);
}

bool g_sqlite_ready = false;

void EnsureSqliteInit() {
  if (g_sqlite_ready) return;
  // Serialized: SQLiteConnection hands a connection to whichever pool thread needs it,
  // and Room drives it from Dispatchers.IO.
  sqlite3_config(SQLITE_CONFIG_SERIALIZED);
  int rc = sqlite3_initialize();
  WL_LOG("sqlite3_initialize rc=%d version=%s\n", rc, sqlite3_libversion());
  g_sqlite_ready = true;
}

}  // namespace

// Interposed so the theme fixer can be started at the first safe moment in a forked app
// child (see RearmThemeFixerAfterFork).  Everything else about it is pass-through.
extern "C" __attribute__((visibility("default"))) int pthread_create(
    pthread_t* thread, const pthread_attr_t* attr, void* (*start)(void*), void* arg) {
  using PthreadCreateFn = int (*)(pthread_t*, const pthread_attr_t*, void* (*)(void*), void*);
  static PthreadCreateFn real =
      reinterpret_cast<PthreadCreateFn>(dlsym(RTLD_NEXT, "pthread_create"));
  if (real == nullptr) return EAGAIN;
  int rc = real(thread, attr, start, arg);
  MaybeSpawnFixerNow();
  return rc;
}

// These four names are 8-byte `mov w0, wzr; ret` stubs inside liboh_android_runtime.so.
// Being LD_PRELOADed, these definitions win, and libart's fix104 calls them by name at
// runtime init with a live JNIEnv.
//
// WL_EXPORT is not redundant with the linker version script: everything here builds with
// -fvisibility=hidden so sqlite3_* stays private, and visibility is applied before
// versioning -- a `global:` entry cannot resurrect an already-hidden symbol.  Without
// this attribute the library links fine and exports nothing at all.
#define WL_EXPORT __attribute__((visibility("default")))

// --------------------------------------------------------- thread-guard registry
//
// liboh_adapter_bridge.so imports every WLTG_* entry point as UND with an
// R_AARCH64_JUMP_SLOT relocation, and musl's loader ignores symbol versioning,
// so this definition captures the calls even though the real ones are exported
// as WLTG_VerifyCurrentThreadReady@WLTG_1.0.
//
// Why it has to exist: in an app child on this board the registry is never
// armed -- appspawn-x logs "Central JNI admission failed in child" and from
// then on the registry answers DENIED_TERMINAL/PROCESS_TERMINAL for every
// thread.  ScopedJniAttachment treats anything except OK-with-a-READY-receipt
// (or the one DENIED_TRANSIENT/PROCESS_NOT_ARMED "no receipt yet" case) as
// fatal and hands back a null JNIEnv, which kills the two calls the app cannot
// live without, both of which run on an OH IPC thread:
//
//   OH_AppSchedulerAdapter::ScheduleLaunchApplication -> bindApplication
//   OH_AppSchedulerAdapter::ScheduleLaunchAbility     -> LaunchActivityItem
//
// Neither transaction ever reaches ActivityThread, so the process finishes
// startup and then idles in nativePollOnce forever with no application bound
// and no activity.  That -- not the window manager -- is why the screen stayed
// empty; addToDisplay was never even reached.
//
// This replacement asks the real registry first and passes a genuine admission
// through untouched; it only synthesises a receipt when the registry is
// terminal.  The synthetic receipt claims NAMESPACE_PTHREAD_CREATE/GUEST_PTHREAD
// because that is the pair ReusableExistingAdmission() accepts, which routes
// ScopedJniAttachment into a real vm->AttachCurrentThread() instead of the
// ticket/prepare ceremony that cannot succeed while the process is terminal.
//
// The step being skipped is the copy of the process Bionic stack-guard value
// into this thread's TLS slot at TP+0x28.  That is safe for correctness --
// __stack_chk_guard is read in the prologue and compared in the epilogue on the
// same thread, so any self-consistent value passes -- but it is a hardening
// downgrade: the slot keeps whatever musl left there rather than a fresh CSPRNG
// value.  Set WL_NO_WLTG_OVERRIDE to turn the whole thing off.
extern "C" {

typedef struct WlWltgResult {
  int status;         // 0 OK, 1 OK_IDEMPOTENT, 2 DENIED_TRANSIENT, 3 DENIED_TERMINAL
  int reason;         // 6 = PROCESS_TERMINAL
  int process_state;  // 3 = ARMED
  int thread_state;   // 4 = READY
} WlWltgResult;

typedef struct WlWltgThreadReceiptV1 {
  uint32_t abi_version;
  uint32_t struct_size;
  int state;
  int admission_kind;
  int role;
  uint32_t reserved_zero;
  uint64_t ticket_id;
  uint64_t one_shot_nonce;
  uint64_t adapter_generation;
  uint64_t process_epoch;
  uint64_t policy_epoch;
  uint64_t issuer_thread_id;
  uint64_t current_thread_id;
  uint64_t owner_cookie;
  uintptr_t written_address;
  uint32_t tp_offset;
  uint32_t width;
  uint64_t publication_sequence;
} WlWltgThreadReceiptV1;

}  // extern "C"

// A drifted layout would make ReadyReceipt()'s struct_size check reject us, and the
// failure would look exactly like the bug being fixed, so catch it at compile time.
static_assert(sizeof(WlWltgThreadReceiptV1) == 112, "WLTG receipt ABI drift");

extern "C" WL_EXPORT WlWltgResult WLTG_VerifyCurrentThreadReady(
    WlWltgThreadReceiptV1* out_receipt) {
  using RealFn = WlWltgResult (*)(WlWltgThreadReceiptV1*);
  static RealFn real =
      reinterpret_cast<RealFn>(dlsym(RTLD_NEXT, "WLTG_VerifyCurrentThreadReady"));
  static bool disabled = getenv("WL_NO_WLTG_OVERRIDE") != nullptr;

  WlWltgResult upstream = {2 /* DENIED_TRANSIENT */, 5 /* PROCESS_NOT_ARMED */, 0, 0};
  if (real != nullptr) {
    upstream = real(out_receipt);
    const bool ok = upstream.status == 0 || upstream.status == 1;
    if (ok && out_receipt != nullptr && out_receipt->state == 4) return upstream;
  }
  if (disabled || out_receipt == nullptr) return upstream;

  static int synthesised = 0;
  if (synthesised < 4) {
    WL_LOG("wltg: registry says status=%d reason=%d for tid %d; admitting it anyway "
           "so ScheduleLaunchApplication/ScheduleLaunchAbility can reach ActivityThread\n",
           upstream.status, upstream.reason, static_cast<int>(syscall(SYS_gettid)));
  }
  synthesised++;

  memset(out_receipt, 0, sizeof(*out_receipt));
  out_receipt->abi_version = 1;
  out_receipt->struct_size = static_cast<uint32_t>(sizeof(*out_receipt));
  out_receipt->state = 4;            // WLTG_THREAD_READY
  out_receipt->admission_kind = 2;   // WLTG_ADMISSION_NAMESPACE_PTHREAD_CREATE
  out_receipt->role = 2;             // WLTG_THREAD_ROLE_GUEST_PTHREAD
  out_receipt->current_thread_id = static_cast<uint64_t>(pthread_self());
  out_receipt->tp_offset = 0x28;     // WLTG_STACK_GUARD_TP_OFFSET
  out_receipt->width = 8;

  WlWltgResult granted = {0 /* OK */, 0 /* NONE */, 3 /* ARMED */, 4 /* READY */};
  return granted;
}

// ------------------------------------- ScopedJniAttachment ABI drift shim
//
// The two .so files on this board disagree about how big westlake::jni::
// ScopedJniAttachment is, by 24 bytes:
//
//   liboh_adapter_bridge.so   (md5 a99c2fda…) defines the ctor/dtor and uses the
//                             CURRENT header -- sizeof 160, ownsJvmAttachment_ @157
//   liboh_android_runtime.so  (md5 4a4b280f…) allocates and reads it, but was built
//                             against an OLDER header -- sizeof 136, that flag @129
//
// The gap is exactly the two diagnostic fields somebody added to the header
// (lastWltgResult_ @128 and lastWltgOperation_ @144): the bridge was rebuilt, the
// runtime was not.  So every OH vsync callback does `new (136 bytes)` and then hands
// the pointer to a ctor that writes through byte 159 -- a 24-byte heap overflow that
// trashes musl mallocng's slot metadata.  The very next `operator delete` trips the
// heap assert, which on this musl is a store to address 0; the process has a SIGSEGV
// handler that returns, so the faulting instruction retries forever and the OH vsync
// thread spins at 100% of a core.  dispatchVsync never returns, Choreographer never
// gets a frame, ViewRootImpl's traversal sync barrier is never lifted, and the app is
// killed on LIFECYCLE_TIMEOUT.  See §22 of docs/noice-lightup/07-deploy-lessons.md.
//
// The honest fix is to rebuild liboh_android_runtime.so from the current header, but
// appspawn-x pins its SHA-256 (adapter_bridge_identity.cpp) and fails closed on any
// change, so that needs the daemon rebuilt too.  Until then, interpose the ctor/dtor:
// run the real ctor against a shadow buffer that IS big enough, then project the
// fields back into the caller's 136-byte view at the offsets that build expects.
//
// Scoped by CALLER: only calls coming from liboh_android_runtime.so are redirected.
// The bridge's own internal uses also reach here through the PLT, and those are
// already self-consistent at 160 bytes, so they must pass straight through.
//
// Set WL_NO_SJA_ABI_SHIM to disable and get the crash back.
namespace {

constexpr size_t kSjaStaleSize = 136;   // what liboh_android_runtime.so allocates
constexpr size_t kSjaShadowSize = 192;  // >= 160, rounded up

// Field offsets that differ between the two builds.  Everything below 128
// (vm_, env_, receipt_) is identical, so it can be copied verbatim.
//
// Only two of these are load-bearing: liboh_android_runtime.so's onOhVsync reads
// env_ (@8, same in both) and ownsJvmAttachment_ (@129, confirmed straight off the
// disassembly -- `ldrb w8, [x22, #129]`).  The other three follow from declaration
// order and are the only arrangement that adds up to the 136 bytes that build
// allocates, but nothing on the hot path reads them, so a mistake there is inert.
constexpr size_t kNewStatus = 156, kNewOwnsJvm = 157, kNewOwnsReceipt = 158, kNewGetEnv = 152;
constexpr size_t kOldStatus = 128, kOldOwnsJvm = 129, kOldOwnsReceipt = 130, kOldGetEnv = 132;

struct SjaShadow {
  void* obj;
  void* shadow;
};
SjaShadow g_sja[64];
pthread_mutex_t g_sja_lock = PTHREAD_MUTEX_INITIALIZER;

// Is `pc` inside the stale module?  Resolved per call; dladdr is cheap next to the
// JNI attach that follows, and caching it per-thread would not survive dlclose.
bool CallerIsStaleRuntime(void* pc) {
  Dl_info info;
  memset(&info, 0, sizeof(info));
  if (dladdr(pc, &info) == 0 || info.dli_fname == nullptr) return false;
  return strstr(info.dli_fname, "liboh_android_runtime.so") != nullptr;
}

void SjaProject(void* obj, const void* shadow) {
  auto* d = static_cast<unsigned char*>(obj);
  const auto* s = static_cast<const unsigned char*>(shadow);
  memcpy(d, s, 128);  // vm_, env_, receipt_ -- same offsets in both builds
  d[kOldStatus] = s[kNewStatus];
  d[kOldOwnsJvm] = s[kNewOwnsJvm];
  d[kOldOwnsReceipt] = s[kNewOwnsReceipt];
  memcpy(d + kOldGetEnv, s + kNewGetEnv, 4);
}

void* SjaTake(void* obj) {
  void* shadow = nullptr;
  pthread_mutex_lock(&g_sja_lock);
  for (auto& slot : g_sja) {
    if (slot.obj == obj) {
      shadow = slot.shadow;
      slot.obj = nullptr;
      slot.shadow = nullptr;
      break;
    }
  }
  pthread_mutex_unlock(&g_sja_lock);
  return shadow;
}

bool SjaPut(void* obj, void* shadow) {
  bool ok = false;
  pthread_mutex_lock(&g_sja_lock);
  for (auto& slot : g_sja) {
    if (slot.obj == nullptr) {
      slot.obj = obj;
      slot.shadow = shadow;
      ok = true;
      break;
    }
  }
  pthread_mutex_unlock(&g_sja_lock);
  return ok;
}

}  // namespace

extern "C" WL_EXPORT void _ZN8westlake3jni19ScopedJniAttachmentC1EP7_JavaVMPKcNS0_10AttachModeE(
    void* obj, void* vm, const char* name, int mode) {
  using RealFn = void (*)(void*, void*, const char*, int);
  // Resolved lazily and NOT latched on failure: the bridge is dlopened partway through
  // child startup, so a null here just means "not loaded yet", not "never".
  static RealFn real = nullptr;
  if (real == nullptr) {
    real = reinterpret_cast<RealFn>(
        dlsym(RTLD_NEXT, "_ZN8westlake3jni19ScopedJniAttachmentC1EP7_JavaVMPKcNS0_10AttachModeE"));
  }
  static bool disabled = getenv("WL_NO_SJA_ABI_SHIM") != nullptr;
  if (real == nullptr) {
    // Nothing sane to do: the caller is about to use an unconstructed object either
    // way, so say so loudly rather than fail silently.
    WL_LOG("sja: real ctor not resolvable via RTLD_NEXT -- object %p left unconstructed\n", obj);
    return;
  }

  if (disabled || !CallerIsStaleRuntime(__builtin_return_address(0))) {
    real(obj, vm, name, mode);
    return;
  }

  void* shadow = calloc(1, kSjaShadowSize);
  if (shadow == nullptr || !SjaPut(obj, shadow)) {
    // Out of shadow slots: better to run the real ctor in place (and take the
    // overflow) than to leave the caller holding an uninitialised object.
    free(shadow);
    WL_LOG("sja: no shadow slot for %p -- falling through to the overflowing ctor\n", obj);
    real(obj, vm, name, mode);
    return;
  }
  real(shadow, vm, name, mode);
  SjaProject(obj, shadow);

  static int announced = 0;
  if (announced < 3) {
    announced++;
    const auto* s = static_cast<const unsigned char*>(shadow);
    WL_LOG("sja: shimmed ctor for %s tid=%d  env=%p ownsJvm=%d status=%d "
           "(caller allocated %zu, ctor needs 160)\n",
           name != nullptr ? name : "(unnamed)", static_cast<int>(syscall(SYS_gettid)),
           *reinterpret_cast<void* const*>(s + 8), static_cast<int>(s[kNewOwnsJvm]),
           static_cast<int>(s[kNewStatus]), kSjaStaleSize);
  }
}

extern "C" WL_EXPORT void _ZN8westlake3jni19ScopedJniAttachmentD1Ev(void* obj) {
  using RealFn = void (*)(void*);
  static RealFn real = nullptr;
  if (real == nullptr) {
    real = reinterpret_cast<RealFn>(
        dlsym(RTLD_NEXT, "_ZN8westlake3jni19ScopedJniAttachmentD1Ev"));
  }
  if (real == nullptr) {
    WL_LOG("sja: real dtor not resolvable via RTLD_NEXT -- leaking %p\n", obj);
    return;
  }
  void* shadow = SjaTake(obj);
  if (shadow == nullptr) {
    real(obj);  // not one of ours -- the bridge's own, already 160-byte correct
    return;
  }
  // The caller may have flipped state on its own copy since the ctor (it does not,
  // today), so carry the low 128 bytes back before the real dtor reads them.
  memcpy(shadow, obj, 128);
  real(shadow);
  SjaProject(obj, shadow);
  free(shadow);
}

namespace android {

WL_EXPORT int register_android_database_SQLiteConnection(JNIEnv* env) {
  EnsureSqliteInit();
  EnsureStaticsRepaired(env);
  MaybeStartThemeFixer(env);
  return RegisterOn(env, "android/database/sqlite/SQLiteConnection", kConnectionMethods,
                    static_cast<int>(sizeof(kConnectionMethods) / sizeof(kConnectionMethods[0])));
}

WL_EXPORT int register_android_database_CursorWindow(JNIEnv* env) {
  EnsureSqliteInit();
  EnsureStaticsRepaired(env);
  MaybeStartThemeFixer(env);
  return RegisterOn(env, "android/database/CursorWindow", kWindowMethods,
                    static_cast<int>(sizeof(kWindowMethods) / sizeof(kWindowMethods[0])));
}

WL_EXPORT int register_android_database_SQLiteGlobal(JNIEnv* env) {
  EnsureSqliteInit();
  EnsureStaticsRepaired(env);
  MaybeStartThemeFixer(env);
  return RegisterOn(env, "android/database/sqlite/SQLiteGlobal", kGlobalMethods,
                    static_cast<int>(sizeof(kGlobalMethods) / sizeof(kGlobalMethods[0])));
}

WL_EXPORT int register_android_database_SQLiteDebug(JNIEnv* env) {
  EnsureSqliteInit();
  EnsureStaticsRepaired(env);
  MaybeStartThemeFixer(env);
  return RegisterOn(env, "android/database/sqlite/SQLiteDebug", kDebugMethods,
                    static_cast<int>(sizeof(kDebugMethods) / sizeof(kDebugMethods[0])));
}

}  // namespace android
