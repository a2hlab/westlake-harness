// 探针专用（SIGCHAIN_PROBE_LOG 编译期开关）：必须在任何 #include 之前定义
// _GNU_SOURCE，才能拿到 aarch64-linux-ohos/bits/signal.h 里 mcontext_t 的具体字段
// （fault_address/regs[31]/sp/pc/pstate），否则拿到的是不透明的
// `long double __regs[18+256]`占位类型，读不出 PC/x21。生产（无宏）编译不受影响。
#ifdef SIGCHAIN_PROBE_LOG
#define _GNU_SOURCE 1
#endif
/*
 * sigchain_muslcompat.cc — musl-compat 转发垫片 for libsigchain.so
 * ===========================================================================
 * WestLake adapter (AOSP-on-OH) · D600 noice 第9步 FREEZE 根因修复
 *
 * 背景（实证报告 _codex_handoff/yue_refs/oh_musl_faulthandler_investigation.md）:
 *   OH 上存在两套互不相通的 sigchain:
 *     - ART 链接 AOSP libsigchain.so（私有 registry chains[_NSIG]）。
 *     - faultloggerd 用 musl 内建 sigchain（third_party/musl/.../sigchain.c，
 *       libc 导出 add_special_signal_handler / add_special_handler_at_last …）。
 *   faultloggerd 的 DFX handler 在库加载期（constructor）以
 *   add_special_handler_at_last() 占住 musl special slot 2 并装内核前端；ART 随后
 *   经 AOSP libsigchain 注册时被 musl intercept_sigaction 降级为"用户兜底 action"，
 *   排在 DFX 之后。隐式 suspend-check 的 spurious SIGSEGV(`ldr x21,[x21]`) 触发时，
 *   musl 先调 DFX → 落 cppcrash 杀进程，ART 的 SuspensionHandler 永远轮不到 →
 *   良性 fault 被当致命崩（D600 noice 第9步 FREEZE）。
 *
 * 修法（方案 A，铁律1 明列的 "OH musl ABI 适配" 例外，libart 源零改）:
 *   把 ART 链接的 libsigchain.so 换成本垫片——保留 AOSP 导出符号名/ABI
 *   （AddSpecialSignalHandlerFn / RemoveSpecialSignalHandlerFn / EnsureFrontOfChain /
 *   SkipAddSignalHandler），内部转发到 musl 的 add_special_signal_handler /
 *   remove_special_signal_handler。这样 ART 的 art_sigsegv_handler 落进 musl 统一
 *   chain 的 slot 0（add_special_signal_handler 填首个空位；DFX 在 slot 2），
 *   musl 派发先调 slot 0 = ART → SuspensionHandler 识别 suspend-check、修 context、
 *   return true → musl "directly return" → DFX 永不跑、零 cppcrash、干净恢复。
 *   精确复刻 bionic 上 ART special handler 先于 debuggerd 跑的行为。
 *
 * 与原 AOSP sigchain.cc 的差异:
 *   - 不再自带 sigaction / sigaction64 / signal / sigprocmask / bsd_signal 拦截器，
 *     也不再 dlopen libc + dlsym linked_sigaction。信号路由统一交给 musl 内建
 *     sigchain（musl 的公开 sigaction 已内置 intercept_sigaction）。
 *   - 不维护 AOSP 私有 chains[_NSIG] registry。
 *
 * /design-check:
 *   - 无 class_linker / vtable / entrypoint 改；libart .cc 源零改（铁律1/3）。
 *   - 落 musl-compat 边界（铁律1 唯一允许重编类别，与 libbionic_compat 同性质）。
 *   - libsigchain.so 非 BCP、不在 boot image → 免 27 段重烤（铁律4）。
 *   - 源码入 aosp_patches/ 可追踪可重编（Alex feedback: 禁二进制补丁）。
 * ===========================================================================
 */

#include <signal.h>
#include <stdint.h>

// ---------------------------------------------------------------------------
// AOSP ABI（被 ART/libart.so 以 weak undef 形式 import 的全部 4 个符号 + 结构）。
// 字段顺序/语义必须与 art/sigchainlib/sigchain.h 严格一致（此处内联以保持垫片
// 自包含，不依赖 AOSP 头在 include path 中）。
// ---------------------------------------------------------------------------
namespace art {

// Handlers that exit without returning (e.g. via siglongjmp) pass this flag.
static constexpr uint64_t SIGCHAIN_ALLOW_NORETURN = 0x1UL;

struct SigchainAction {
  bool (*sc_sigaction)(int, siginfo_t*, void*);
  sigset_t sc_mask;
  uint64_t sc_flags;
};

}  // namespace art

// ---------------------------------------------------------------------------
// musl ABI（OH libc 导出；见 sysroot include/aarch64-linux-ohos/sigchain.h 与
// third_party/musl/.../src/sigchain/sigchain.c）。在此声明，由 -lc 在链接期解析。
// ---------------------------------------------------------------------------
extern "C" {

struct signal_chain_action {
  bool (*sca_sigaction)(int, siginfo_t*, void*);
  sigset_t sca_mask;
  int sca_flags;
};

// add_special_signal_handler: 填 musl special chain 首个空 slot（=slot 0，若 ART
// 先于其它 special handler 注册），并 mark + 装内核前端。
void add_special_signal_handler(int signo, struct signal_chain_action* sa);
// remove_special_signal_handler: 从 musl special chain 移除指定 handler。
void remove_special_signal_handler(int signo, bool (*fn)(int, siginfo_t*, void*));

}  // extern "C"

// ---------------------------------------------------------------------------
// ★诊断专用探针（SIGCHAIN_PROBE_LOG，默认不编译，byte-identical 于生产版本）。
// 2026-07-10 route3 sigchain 假说账本"下一步建议"（memory
// route3-rssurface-stack-confirmed.md §"执行上一节…sigchain修复实测部署验证"）：
// 部署缺口已证伪（.so 已加载进崩溃进程），但"注册/调用链是否真正介入这次崩溃"仍
// not_proven。本探针在 codex 建议的最小侵入基础上做了一处刻意扩展：不只在
// AddSpecialSignalHandlerFn 记一次调用计数（只能证明"注册发生过"），还把 ART 传入
// 的 sc_sigaction 包一层 thunk，在信号真正打过来时也记一行（能证明"崩溃发生时信号
// 是否路由到了我们这层、以及 ART 自己的 handler 返回 true/false"）——这是区分候选
// (b)(c)（信号从未到达）vs (e)(f)（到达但 ART 自己判定失败）所必需的，仅凭调用计数
// 做不到。全程只用 write()/getpid()/syscall(SYS_gettid) 等 async-signal-safe 原语，
// 手写整数转字符串，不在信号上下文调用 snprintf/malloc，避免探针自己引入新的不稳定
// 混淆信号处理路径本身。
// ---------------------------------------------------------------------------
#ifdef SIGCHAIN_PROBE_LOG
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <stdint.h>
#include <time.h>
#include <link.h>     // dl_iterate_phdr / struct dl_phdr_info — L3 探针用
#include <string.h>   // strstr/memcpy — L3 探针用（非信号上下文，libc 调用安全）

namespace sigchain_probe {

constexpr const char* kLogPath = "/data/local/tmp/sigchain_probe.log";
// build tag：每次改探针逻辑手动改这个字符串，日志里能反查是哪一版二进制在跑。
// v2（codex round1 挑刺后）：加 ucontext PC/x21/SP/fault_address 提取，直接跟
// tombstone 的 pc=boot.oat+0x20e7d0 / x21=0 逐字段比对，不再只靠 pid/tid/addr/code
// 这种弱 identity（codex 指出同一 tid 死前有 3-4 次同 signature 良性 fault，弱
// identity 不足以证明"最后一条 INVOKE 就是 tombstone 那一次")。
// v3（"sigchain返回true仍fatal"悖论只读预研 candidate 2A，2026-07-10 未部署）：
// 诊断树第2层——handled==1 时 redirect 是否真的按 AOSP SuspensionHandler::Action
// 预期落地（mc->pc 改写为 art_quick_implicit_suspend、mc->regs[30]=故障pc+4）。
// 在调用 g_real_handler(...) 之后，重新读一次同一个 ucontext 的 pc/regs[30]/x21，
// 追加为 post_pc/post_lr/post_x21。符号化（post_pc 是否等于 art_quick_implicit_
// suspend 的运行时地址）留给线下：同一进程崩溃时刻的 /proc/pid/maps 快照 +
// 事后对同一块 libart.so 二进制 readelf/nm/llvm-objdump 反查，此处不引入
// dl_iterate_phdr/地址解析，只留原始整数（design-check 记录见候选2A predefined
// 范围：不做符号化、不做重试逻辑、不改变 handled 的返回值/控制流）。
// v4（第二轮ACH综合"给下一个agent的具体动作清单②"合并插桩，2026-07-10）：在 v3
// candidate 2A 基础上一次性补齐 codex round2 点名的字段，避免分批碰设备。补充
// 动机见 premortem_v4.md（_radar_rigor §4）：
//   - has_ctx：区分 uc==nullptr 与"读到真实值0"，避免 post_pc=0 的歧义误读成
//     "redirect 把 pc 改写成了一个不合理的0值"。
//   - pre_lr：调用前的 regs[30]，与 post_lr 做同一次信号内部的前后对照（而不是
//     跨信号弱比对），用于交叉验证 post_lr==故障pc+4 这一 AOSP 预期字面语义。
//   - reentry_depth：只读原子计数器，探测同一信号处理路径是否被重入，不改变
//     控制流；用于把"redirect 未生效/已生效"之外的第三种异常模式先排除重入
//     这一更平凡的解释，而不是直接坐实到 L2/L3 机制本身。
//   - ts_sec/ts_ns：CLOCK_REALTIME（非 MONOTONIC——要跟 hilog 的 wall-clock
//     时间戳强关联，用于交叉核对 ghost tid、MUSL-SIGCHAIN 记录的时间顺序）。
//   - handler_ptr：g_real_handler[signo] 的地址值，只是"同一个 handler 函数
//     指针"的代理身份，明确不等价于 musl signal_chain_handler() 派发循环里的
//     真实 slot idx（本轮任务范围不碰 musl 该源码本体，做不到真正的
//     handler_index，如实标注为近似）。
// v5（codex round1 挑刺后追加，2026-07-10）：非信号上下文一次性解析
// /proc/self/maps 拿 libart.so RX 段 load bias（log_libart_base()，见下方
// 实现），把 post_pc 的符号化从"低12位页内偏移吻合"升级为可核算的
// "post_pc - load_bias == art_quick_implicit_suspend 文件偏移"完整证明链，
// 不新增任何信号上下文开销。
// v6（PhaseB真机整合插桩回合，2026-07-10）：L3 flags-counter 探针——按 memory
// route3-rssurface-stack-confirmed.md"路线②预研"一节给出的 next-step recipe
// 严格实现（不重新设计）：在 art::Thread::artImplicitSuspendFromCode 函数
// 入口（部署版 libart.so md5 3390d67932867c2cca06aa1322d15cc0，地址
// 0x7fd7ac，本轮已用 nm -S + llvm-objdump 对当前部署版重新核验，逐字节吻合
// route②记录的地址/指令）整体挂钩：不在 tst(0x7fd7c0)/b.ne(0x7fd7c4) 之间插
// 任何代码（避免破坏 NZCV），而是劫持函数入口前 4 条指令（stp x29,x30,[sp,#-32]!
// / stp x20,x19,[sp,#16] / mov x29,sp / ldr w8,[x0]，共 16 字节），trampoline
// 原样重放这 4 条指令后跳回 tst 指令之前的原始位置（0x7fd7ac+0x10）继续执行——
// 此时真正的 tst 尚未运行，效果与"从未被劫持"完全一致，故不需要 mrs/msr NZCV
// 显式保存（这是 recipe 建议的"不破坏控制流的等价 trampoline"具体实现，非另一
// 种独立设计）。地址解析改用 dl_iterate_phdr()（比 v5 log_libart_base() 手工
// 解析 /proc/self/maps 更稳健——v5 那次曾因手工解析出现未查明的 0x800 残差，
// dl_iterate_phdr 是标准 libc/musl API，直接给出正确的 load bias，避免同一类
// 方法论坑）。安装时机：复用已证明安全的 AddSpecialSignalHandlerFn 首次调用点
// （FaultManager::Init 时刻，非信号上下文，早于任何托管代码执行，不引入新的
// 未验证时机）。读数写入同一 sigchain_probe.log 文件，同 pid，离线读取——不
// 新增日志机制。
// v7：在每次进入 ART special handler 前，用 raw rt_sigaction query 读取内核当前
// disposition。若 Unity 的 bionic-ABI signal box 把自己的 crash handler 安在
// musl signal_chain_handler 外层，这里看到的 handler 应落在 libunity.so；若仍
// 是 musl front-end，则该假说被直接证伪。query 只读内核状态，不改 handler。
constexpr const char* kBuildTag = "sigchain_probe_v7_kernel_action_20260710";

static int g_fd = -1;
static volatile long g_add_call_count = 0;
static volatile long g_invoke_call_count = 0;
static volatile long g_reentry_depth = 0;
static volatile long g_l3_total_calls = 0;
static volatile long g_l3_nonzero_calls = 0;
static bool g_l3_patch_installed = false;
static bool (*g_real_handler[64])(int, siginfo_t*, void*) = {};

// aarch64 kernel rt_sigaction ABI。不能用 musl struct sigaction：后者含 128-byte
// userspace sigset_t，而 raw syscall 的 kernel sigsetsize 固定为 8 bytes。
struct KernelSigaction {
  unsigned long handler;
  unsigned long flags;
  unsigned long restorer;
  uint64_t mask;
};

struct KernelActionSnapshot {
  KernelSigaction action = {};
  long rc = -1;
  int query_errno = 0;
};

static KernelActionSnapshot query_kernel_action(int signo) {
  KernelActionSnapshot out;
  out.rc = syscall(SYS_rt_sigaction, signo, nullptr, &out.action,
                   static_cast<size_t>(8));
  out.query_errno = out.rc == 0 ? 0 : errno;
  return out;
}

// 手写十进制/十六进制格式化，避免在信号上下文使用非 async-signal-safe 的
// snprintf/sprintf。
static int fmt_u64_dec(unsigned long long v, char* out) {
  char tmp[24];
  int n = 0;
  if (v == 0) { out[0] = '0'; return 1; }
  while (v > 0 && n < (int)sizeof(tmp)) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
  for (int i = 0; i < n; i++) out[i] = tmp[n - 1 - i];
  return n;
}

static int fmt_i64_dec(long long v, char* out) {
  if (v < 0) {
    out[0] = '-';
    return 1 + fmt_u64_dec((unsigned long long)(-v), out + 1);
  }
  return fmt_u64_dec((unsigned long long)v, out);
}

static int fmt_u64_hex(unsigned long long v, char* out) {
  static const char* kDigits = "0123456789abcdef";
  char tmp[16];
  int n = 0;
  if (v == 0) { out[0] = '0'; return 1; }
  while (v > 0 && n < (int)sizeof(tmp)) { tmp[n++] = kDigits[v & 0xf]; v >>= 4; }
  for (int i = 0; i < n; i++) out[i] = tmp[n - 1 - i];
  return n;
}

// 固定大小行缓冲，越界直接截断（诊断专用，字段值都是小整数，实践中不会触顶）。
struct LineBuf {
  char buf[384];
  int len = 0;
  void lit(const char* s) { while (*s && len < (int)sizeof(buf) - 1) buf[len++] = *s++; }
  void dec(long long v) {
    if (len >= (int)sizeof(buf) - 24) return;
    len += fmt_i64_dec(v, buf + len);
  }
  void hex(unsigned long long v) {
    lit("0x");
    if (len >= (int)sizeof(buf) - 20) return;
    len += fmt_u64_hex(v, buf + len);
  }
};

static void ensure_open() {
  if (g_fd < 0) {
    g_fd = open(kLogPath, O_WRONLY | O_CREAT | O_APPEND, 0666);
  }
}

static void write_line(const LineBuf& L) {
  if (g_fd >= 0 && L.len > 0) {
    write(g_fd, L.buf, (size_t)L.len);
  }
}

// v5（codex round1 挑刺，2026-07-10）："post_pc 低12位页内偏移与 art_quick_
// implicit_suspend 文件偏移低12位吻合"只是强旁证，不是完整地址证明——必须用
// 该进程实际的 libart.so RX 段 load bias 验证 post_pc-load_bias==符号文件
// 偏移，才是逐字节确认。这一步刻意放在**非信号上下文**（ART FaultManager::
// Init 调用 AddSpecialSignalHandlerFn 时，进程刚起步、远早于任何崩溃）完成，
// 只解析一次 /proc/self/maps 缓存全局变量，代价是进程启动时的一次性开销，
// **不在信号处理路径里新增任何 open()/read() 操作**——既回应 codex 对符号化
// 严谨性的要求，又不引入 codex 同时指出的"新的信号上下文开销可能扰动竞态
// 时序"这个相反风险，两者不冲突。只读，不改变任何控制流。
static unsigned long g_libart_base = 0;

static void log_libart_base() {
  int fd = open("/proc/self/maps", O_RDONLY);
  if (fd < 0) return;
  char buf[4096];
  char line[512];
  int line_len = 0;
  ssize_t r;
  while ((r = read(fd, buf, sizeof(buf))) > 0 && g_libart_base == 0) {
    for (ssize_t i = 0; i < r; i++) {
      char c = buf[i];
      if (c == '\n') {
        line[line_len < (int)sizeof(line) ? line_len : (int)sizeof(line) - 1] = '\0';
        bool has_libart = false, has_rxp = false;
        for (int j = 0; j + 9 <= line_len; j++) {
          if (line[j]=='l'&&line[j+1]=='i'&&line[j+2]=='b'&&line[j+3]=='a'&&
              line[j+4]=='r'&&line[j+5]=='t'&&line[j+6]=='.'&&line[j+7]=='s'&&
              line[j+8]=='o') { has_libart = true; break; }
        }
        for (int j = 0; j + 4 <= line_len; j++) {
          if (line[j]=='r'&&line[j+1]=='-'&&line[j+2]=='x'&&line[j+3]=='p') {
            has_rxp = true; break;
          }
        }
        if (has_libart && has_rxp) {
          unsigned long addr = 0;
          int k = 0;
          while (k < line_len && line[k] != '-') {
            char ch = line[k];
            int digit = -1;
            if (ch >= '0' && ch <= '9') digit = ch - '0';
            else if (ch >= 'a' && ch <= 'f') digit = ch - 'a' + 10;
            else if (ch >= 'A' && ch <= 'F') digit = ch - 'A' + 10;
            if (digit < 0) break;
            addr = (addr << 4) | (unsigned long)digit;
            k++;
          }
          g_libart_base = addr;
          line_len = 0;
          break;
        }
        line_len = 0;
      } else if (line_len < (int)sizeof(line) - 1) {
        line[line_len++] = c;
      }
    }
  }
  close(fd);
}

// 非信号上下文（ART FaultManager::Init 直接调用），可以安全 open()。
static void log_register(int signo, uint64_t sc_flags) {
  long n = __sync_add_and_fetch(&g_add_call_count, 1);
  ensure_open();
  log_libart_base();  // v5: 只在首次 REGISTER 时解析一次，非信号上下文。
  LineBuf L;
  L.lit("REGISTER build="); L.lit(kBuildTag);
  L.lit(" pid="); L.dec(getpid());
  L.lit(" tid="); L.dec((long long)syscall(SYS_gettid));
  L.lit(" signo="); L.dec(signo);
  L.lit(" sc_flags="); L.hex(sc_flags);
  L.lit(" add_call_count="); L.dec(n);
  L.lit(" errno="); L.dec(errno);
  L.lit(" libart_base="); L.hex(g_libart_base);
  L.lit("\n");
  write_line(L);
}

// ---------------------------------------------------------------------------
// v6 L3 flags-counter 探针：函数入口挂钩安装（route②预研 next-step recipe
// 严格照做，见本 section 顶部大注释）。trampoline 汇编体在文件末尾（全局
// extern "C" 符号 l3_trampoline_entry），此处只做地址解析 + 代码页可写切换 +
// 16 字节 patch 写入 + I-cache flush，全部发生在 AddSpecialSignalHandlerFn
// 首次调用这个已证明安全的非信号上下文，不引入新的信号上下文开销。
//
// ★已知局限（如实记录，codex round1 复核后补全，非发布后补丁）：
//   1. 硬编码偏移/无版本自适应：见下方 kArtImplicitSuspendOffset 注释——
//      写入前已加 memcmp 预期指令字节的 fail-closed 校验（不匹配则放弃
//      patch，不盲写），但这只挡住"完全对不上"的情况，挡不住"字节凑巧
//      相同但语义已变"这种理论上存在、实践中概率极低的情况。
//   2. **这个 hook 一旦安装，对进程内全部线程、该函数的全部后续调用都生
//      效**，不是只针对触发目标崩溃签名的那一次调用——因为
//      artImplicitSuspendFromCode 只能经 art_quick_implicit_suspend（只能
//      经 SuspensionHandler 的信号重定向到达，见 route②源码级拆解），本
//      项目历史数据显示这个函数在目标进程短暂生命周期内总调用次数很低
//      （candidate 2A 8 次 truly-cold 共观测到约 76 次 INVOKE，粗略对应
//      量级），不是传统意义上的高频热路径，但如实标注"全局生效"这个事实，
//      不遗漏。
//   3. patch 安装用 CAS 保证只有一个线程真正执行安装（见 l3_install_patch()
//      内 __sync_bool_compare_and_swap），但**没有、也无法在探针范围内做到
//      "安装那一刻确保没有任何线程正在执行被覆盖的原始 4 条指令"**——这需要
//      stop-the-world 式的全线程暂停，超出一个诊断探针的合理范围。缓解
//      依据：安装时机是 FaultManager::Init（Runtime 初始化早期，非信号
//      上下文），根据 L3 源码级拆解，此时不可能已有线程走到隐式 suspend-
//      check 重定向路径（该路径本身要求 Runtime 已完全初始化、托管代码已
//      开始执行），故这个残余竞态窗口在设计上不可达，但没有代码层面的强制
//      保证，如实记录为已知局限而非"已证明不可能"。
//   4. BTI（Branch Target Identification）：若目标设备内核/编译器为
//      libart.so 启用了 BTI，我们的 `br x16`/`br x9` 落点如果不是合法
//      landing pad（`bti c`/`bti j` 指令）会触发异常。本轮未核实 5eab
//      设备/该 libart.so 编译时是否启用 BTI，如实标注为未验证项，不是
//      "已确认安全"。
//   5. 恢复页保护失败（mprotect 第二次调用）不再静默吞掉——见下方
//      l3_install_patch() 内 restore_ok 分支，日志区分 status=ok 与
//      status=ok_but_restore_prot_failed。
// ---------------------------------------------------------------------------
// hidden：避免 trampoline 里那条 `bl l3_probe_record` 走 PLT 间接跳转
// （intra-.so 调用没有理由允许运行时符号抢占），在这个极度敏感的执行点少一
// 层间接。l3_trampoline_entry 只是取地址嵌进 patch stub，hidden 不影响这个
// 用法，只是同样去掉不必要的 GOT/PLT 项。
extern "C" __attribute__((visibility("hidden"))) void
l3_probe_record(unsigned int flags);
extern "C" __attribute__((visibility("hidden"))) void
l3_trampoline_entry(void);
// hidden visibility：g_l3_resume_addr 只在本 .so 内部使用（trampoline 汇编
// 用 adrp/`:lo12:` 直接寻址），标 hidden 让链接器按"不可被外部抢占"处理，
// 否则 -fPIC 下默认 visibility 的全局符号需要走 GOT 间接寻址，plain
// adrp+add:lo12: 会在链接期报 R_AARCH64_ADR_PREL_PG_HI21 错误（已实测踩过，
// 如实记录）。
extern "C" __attribute__((visibility("hidden")))
volatile unsigned long g_l3_resume_addr;

// route②"最高优先级"静态核验（本轮 2026-07-10 用当前部署版 libart.so md5
// 3390d67932867c2cca06aa1322d15cc0 重新核验，逐字节吻合 memory 记录）：
// artImplicitSuspendFromCode @ 0x7fd7ac，前 4 条指令 = stp x29,x30,[sp,#-32]!
// / stp x20,x19,[sp,#16] / mov x29,sp / ldr w8,[x0]（共 16 字节，恰好等于
// 我们要写入的 16 字节 far-branch stub 大小，不会截断/覆盖到第 5 条指令）。
// 此偏移只对该 md5 成立；探针本身不做 libart.so md5 校验/版本自适应（design-
// check 已知边界，如实标注）——若设备侧后续 OTA/固件更新导致该 md5 变化，
// 这个硬编码偏移可能指向错误位置；l3_install_patch() 内已加 memcmp 预期
// 指令字节的 fail-closed 校验缓解（见上方"已知局限"第 1 条），不是完全
// 消除。事后核对手段：探针只读日志里的 libart_base 供人工/脚本比对，不在
// 探针内部引入 md5 计算这类重量级运行时开销。
static const unsigned long kArtImplicitSuspendOffset = 0x7fd7acUL;

static int find_libart_phdr_cb(struct dl_phdr_info* info, size_t /*size*/,
                                void* data) {
  unsigned long* out_base = reinterpret_cast<unsigned long*>(data);
  if (info->dlpi_name != nullptr && info->dlpi_name[0] != '\0' &&
      strstr(info->dlpi_name, "libart.so") != nullptr) {
    *out_base = info->dlpi_addr;
    return 1;  // 非 0 = 停止 dl_iterate_phdr 遍历
  }
  return 0;
}

static void l3_install_patch() {
  // codex round1：原来的 "if (bool) return; bool=true;" 不是原子的，两个线程
  // 并发首次调用 AddSpecialSignalHandlerFn（SIGSEGV/SIGBUS 各注册一次，理论
  // 上可能被不同线程触发）可能都通过检查、都尝试 patch。改用 CAS，保证只有
  // 一个线程真正执行安装，其余线程立即返回。
  if (!__sync_bool_compare_and_swap(&g_l3_patch_installed, false, true)) {
    return;
  }

  LineBuf L;
  L.lit("L3_INSTALL build="); L.lit(kBuildTag);
  L.lit(" pid="); L.dec(getpid());

  // dl_iterate_phdr 而非手工解析 /proc/self/maps（v5 曾在后者上踩过一个
  // 未查明来源的 0x800 残差坑，见 kBuildTag=v5 注释）——dl_iterate_phdr 是
  // 标准 libc/musl API，dlpi_addr 就是正确的 load bias，不需要额外核算。
  unsigned long libart_base = 0;
  dl_iterate_phdr(find_libart_phdr_cb, &libart_base);
  if (libart_base == 0) {
    L.lit(" status=libart_not_found\n");
    write_line(L);
    return;
  }

  unsigned long target = libart_base + kArtImplicitSuspendOffset;

  // codex round1 阻断性意见：写 patch 前没有校验目标 16 字节确实是预期的
  // 4 条指令——如果部署版 libart.so 的 md5/偏移和本探针硬编码的
  // 0x7fd7ac 不一致（OTA/固件更新/不同设备），会往任意代码位置写 16 字节，
  // 后果不可控。加 fail-closed 校验：不匹配就只打日志、放弃 patch。
  static const uint32_t kExpected[4] = {
      0xa9be7bfdu,  // stp x29, x30, [sp, #-32]!
      0xa9014ff4u,  // stp x20, x19, [sp, #16]
      0x910003fdu,  // mov x29, sp
      0xb9400008u,  // ldr w8, [x0]
  };
  uint32_t actual[4];
  __builtin_memcpy(actual, reinterpret_cast<const void*>(target), 16);
  if (actual[0] != kExpected[0] || actual[1] != kExpected[1] ||
      actual[2] != kExpected[2] || actual[3] != kExpected[3]) {
    L.lit(" status=instr_mismatch libart_base="); L.hex(libart_base);
    L.lit(" target="); L.hex(target);
    L.lit(" got0="); L.hex(actual[0]);
    L.lit(" got1="); L.hex(actual[1]);
    L.lit(" got2="); L.hex(actual[2]);
    L.lit(" got3="); L.hex(actual[3]);
    L.lit("\n");
    write_line(L);
    return;
  }

  long pagesize = sysconf(_SC_PAGESIZE);
  if (pagesize <= 0) pagesize = 4096;
  unsigned long page_start =
      target & ~(unsigned long)(pagesize - 1);
  unsigned long page_end =
      (target + 16 + (unsigned long)pagesize - 1) &
      ~(unsigned long)(pagesize - 1);

  if (mprotect(reinterpret_cast<void*>(page_start), page_end - page_start,
               PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
    L.lit(" status=mprotect_rw_failed errno="); L.dec(errno);
    L.lit(" libart_base="); L.hex(libart_base);
    L.lit(" target="); L.hex(target);
    L.lit("\n");
    write_line(L);
    return;
  }

  // trampoline 结束后跳回被劫持的 4 条指令之后（tst 指令之前）——16 字节 =
  // 被覆盖的 4 条指令的确切长度，不多不少。
  g_l3_resume_addr = target + 16;

  unsigned char patch[16];
  uint32_t insn_ldr_x16_lit8 = 0x58000050u;  // ldr x16, #8
  uint32_t insn_br_x16       = 0xd61f0200u;  // br  x16
  unsigned long tramp_addr =
      reinterpret_cast<unsigned long>(&l3_trampoline_entry);
  __builtin_memcpy(patch, &insn_ldr_x16_lit8, 4);
  __builtin_memcpy(patch + 4, &insn_br_x16, 4);
  __builtin_memcpy(patch + 8, &tramp_addr, 8);
  __builtin_memcpy(reinterpret_cast<void*>(target), patch, 16);

  // 写回原保护位（r-xp），不长期保留 w+x 页；codex round1 指出原代码忽略了
  // 这次 mprotect 的返回值——若失败会长期留下 RWX 页，但日志仍写 status=ok，
  // 现在如实区分。
  bool restore_ok =
      (mprotect(reinterpret_cast<void*>(page_start), page_end - page_start,
                PROT_READ | PROT_EXEC) == 0);
  __builtin___clear_cache(reinterpret_cast<char*>(target),
                           reinterpret_cast<char*>(target) + 16);

  L.lit(restore_ok ? " status=ok" : " status=ok_but_restore_prot_failed");
  L.lit(" restore_errno="); L.dec(restore_ok ? 0 : errno);
  L.lit(" libart_base="); L.hex(libart_base);
  L.lit(" target="); L.hex(target);
  L.lit(" trampoline="); L.hex(tramp_addr);
  L.lit(" resume="); L.hex(g_l3_resume_addr);
  L.lit("\n");
  write_line(L);
}

// 信号上下文：只用 async-signal-safe 原语（write/getpid/syscall），不 open() 不
// malloc；ensure_open() 已在 log_register 阶段（非信号上下文）跑过，这里 g_fd 应
// 已就绪，若未就绪则本行静默丢弃（不在信号里补 open()）。
static bool probe_thunk(int signo, siginfo_t* info, void* ctx) {
  const int entry_errno = errno;
  long n = __sync_add_and_fetch(&g_invoke_call_count, 1);
  // v4: 只读重入探测——不加锁、不改变控制流，仅用于分析阶段区分"redirect 未/已
  // 生效"之外的第三种异常模式是否只是同一路径被重入（premortem_v4.md 混淆源3）。
  long depth_on_entry = __sync_add_and_fetch(&g_reentry_depth, 1);
  // v4: CLOCK_REALTIME（非 MONOTONIC）——要跟 hilog 的 wall-clock 时间戳直接
  // 强关联，用来交叉核对 ghost tid / MUSL-SIGCHAIN 记录的时间顺序。
  // clock_gettime 是 async-signal-safe 的系统调用包装，可在信号上下文调用。
  struct timespec ts_entry = {0, 0};
  clock_gettime(CLOCK_REALTIME, &ts_entry);
  KernelActionSnapshot kernel_action = query_kernel_action(signo);
  // ucontext 精确身份字段：直接跟 tombstone 的 pc/x21/sp 逐字段比对，而不是只靠
  // pid/tid/si_addr/si_code 这种弱 identity（codex round1 指出同一 tid 死前有
  // 多次同 signature 的良性 fault，弱 identity 分不清"最后一条就是致命那条"）。
  unsigned long ctx_pc = 0, ctx_x21 = 0, ctx_sp = 0, ctx_faultaddr = 0;
  unsigned long ctx_lr = 0;  // v4 pre_lr：调用前 regs[30]，供事后与 post_lr 对照。
  int has_ctx = 0;           // v4：区分 uc==nullptr 与"读到真实值0"。
  // v3: 提到外层作用域，供调用 g_real_handler 之后的 post_* 读回复用同一个
  // ucontext 指针（候选2A：只读，不改 handler 语义/控制流）。
  ucontext_t* uc = nullptr;
  if (ctx != nullptr) {
    uc = reinterpret_cast<ucontext_t*>(ctx);
    has_ctx = 1;
    ctx_pc = uc->uc_mcontext.pc;
    ctx_sp = uc->uc_mcontext.sp;
    ctx_faultaddr = uc->uc_mcontext.fault_address;
    ctx_x21 = uc->uc_mcontext.regs[21];  // aarch64 x21：目标签名的关键寄存器
    ctx_lr = uc->uc_mcontext.regs[30];   // v4 pre_lr
  }
  // v4 handler_ptr：g_real_handler[signo] 的地址值，只是"同一个 handler 函数
  // 指针"的代理身份，不是 musl 派发循环里的真实 slot idx（任务范围不碰 musl
  // signal_chain_handler() 本体，做不到字面意义的 handler_index，如实近似）。
  unsigned long handler_ptr = 0;
  if (signo >= 0 && signo < 64) {
    handler_ptr = reinterpret_cast<unsigned long>(g_real_handler[signo]);
  }
  {
    LineBuf L;
    L.lit("INVOKE build="); L.lit(kBuildTag);
    L.lit(" pid="); L.dec(getpid());
    L.lit(" tid="); L.dec((long long)syscall(SYS_gettid));
    L.lit(" signo="); L.dec(signo);
    L.lit(" si_signo="); L.dec(info ? info->si_signo : -1);
    L.lit(" code="); L.dec(info ? info->si_code : -1);
    L.lit(" addr="); L.hex(info ? (unsigned long long)(uintptr_t)info->si_addr : 0ULL);
    L.lit(" ctx_pc="); L.hex(ctx_pc);
    L.lit(" ctx_x21="); L.hex(ctx_x21);
    L.lit(" ctx_sp="); L.hex(ctx_sp);
    L.lit(" ctx_faultaddr="); L.hex(ctx_faultaddr);
    L.lit(" has_ctx="); L.dec(has_ctx);
    L.lit(" pre_lr="); L.hex(ctx_lr);
    L.lit(" handler_ptr="); L.hex(handler_ptr);
    L.lit(" reentry_depth="); L.dec(depth_on_entry);
    L.lit(" ts_sec="); L.dec((long long)ts_entry.tv_sec);
    L.lit(" ts_ns="); L.dec((long long)ts_entry.tv_nsec);
    L.lit(" invoke_count="); L.dec(n);
    L.lit("\n");
    write_line(L);
  }
  {
    LineBuf L;
    L.lit("KERNEL_ACTION build="); L.lit(kBuildTag);
    L.lit(" pid="); L.dec(getpid());
    L.lit(" tid="); L.dec((long long)syscall(SYS_gettid));
    L.lit(" signo="); L.dec(signo);
    L.lit(" invoke_count="); L.dec(n);
    L.lit(" handler="); L.hex(kernel_action.action.handler);
    L.lit(" flags="); L.hex(kernel_action.action.flags);
    L.lit(" restorer="); L.hex(kernel_action.action.restorer);
    L.lit(" mask="); L.hex(kernel_action.action.mask);
    L.lit(" query_rc="); L.dec(kernel_action.rc);
    L.lit(" query_errno="); L.dec(kernel_action.query_errno);
    L.lit("\n");
    write_line(L);
  }
  bool handled = false;
  errno = entry_errno;
  if (signo >= 0 && signo < 64 && g_real_handler[signo] != nullptr) {
    handled = g_real_handler[signo](signo, info, ctx);
  }
  // v3 候选2A：调用后重新读同一个 uc（若非空）——ART 的 SuspensionHandler::Action
  // 在 handled==true 时会就地改写 mc->pc（改到 art_quick_implicit_suspend）和
  // mc->regs[30]（LR=故障pc+4），handled==false 时这里应与调用前的 ctx_pc/ctx_x21
  // 相同（handler 没碰 context）。只读回读，不做任何判断/分支，留给线下符号化。
  unsigned long post_pc = 0, post_lr = 0, post_x21 = 0;
  if (uc != nullptr) {
    post_pc = uc->uc_mcontext.pc;
    post_lr = uc->uc_mcontext.regs[30];
    post_x21 = uc->uc_mcontext.regs[21];
  }
  struct timespec ts_exit = {0, 0};
  clock_gettime(CLOCK_REALTIME, &ts_exit);
  long depth_on_exit = __sync_sub_and_fetch(&g_reentry_depth, 1);
  {
    LineBuf L;
    L.lit("INVOKE_RESULT invoke_count="); L.dec(n);
    L.lit(" signo="); L.dec(signo);
    L.lit(" ctx_pc="); L.hex(ctx_pc);
    L.lit(" handled="); L.dec(handled ? 1 : 0);
    L.lit(" has_ctx="); L.dec(has_ctx);
    L.lit(" post_pc="); L.hex(post_pc);
    L.lit(" post_lr="); L.hex(post_lr);
    L.lit(" post_x21="); L.hex(post_x21);
    L.lit(" pre_lr="); L.hex(ctx_lr);
    L.lit(" reentry_depth_exit="); L.dec(depth_on_exit);
    L.lit(" ts_sec="); L.dec((long long)ts_exit.tv_sec);
    L.lit(" ts_ns="); L.dec((long long)ts_exit.tv_nsec);
    L.lit("\n");
    write_line(L);
  }
  errno = entry_errno;
  return handled;
}

}  // namespace sigchain_probe

// ---------------------------------------------------------------------------
// v6 L3 trampoline 落地点（extern "C"，文件作用域，供上面 l3_install_patch()
// 里的 16 字节 far-branch stub 跳入，以及内联汇编里的符号名引用）。
// ---------------------------------------------------------------------------

// 实际存储定义（327 行附近的 `extern "C" volatile unsigned long
// g_l3_resume_addr;` 只是声明，供 l3_install_patch() 在本定义之前就能引用；
// 真正的存储在此处，且必须是非 static 的普通全局，才能被下面 file-scope
// 内联汇编用 `adrp`/`:lo12:` 按符号名直接寻址）。
extern "C" __attribute__((visibility("hidden")))
volatile unsigned long g_l3_resume_addr = 0;

// l3_probe_record: 由 trampoline 汇编体 `bl` 调用，运行在被劫持函数的调用者
// 栈帧上（sigreturn 之后的正常线程上下文，非信号处理器上下文——见本文件
// "v6 L3 flags-counter 探针" 大注释）。只做原子计数 + 复用既有 write_line()
// 基础设施写一行日志，不 open()/malloc（沿用 probe_thunk 同一条谨慎纪律，
// 即使这里技术上不是真正的信号上下文）。
extern "C" __attribute__((visibility("hidden")))
void l3_probe_record(unsigned int flags) {
  long n = __sync_add_and_fetch(&sigchain_probe::g_l3_total_calls, 1);
  // codex round2 非阻断意见：flags==0 时原代码 nz 恒为局部 0，日志会打印
  // "nonzero_count=0"，即使全局累计值其实已经 >0——具有误导性。改成不管
  // 是否本次命中都读一次当前累计值（用 __sync_add_and_fetch(...,0) 做一次
  // 原子读，避免裸读 volatile 在多核上的可见性歧义）。
  if (flags != 0) {
    __sync_add_and_fetch(&sigchain_probe::g_l3_nonzero_calls, 1);
  }
  long nz = __sync_add_and_fetch(&sigchain_probe::g_l3_nonzero_calls, 0);
  struct timespec ts = {0, 0};
  clock_gettime(CLOCK_REALTIME, &ts);
  sigchain_probe::LineBuf L;
  L.lit("L3_FLAGS build="); L.lit(sigchain_probe::kBuildTag);
  L.lit(" pid="); L.dec(getpid());
  L.lit(" tid="); L.dec((long long)syscall(SYS_gettid));
  L.lit(" flags="); L.hex(flags);
  L.lit(" nonzero="); L.dec(flags != 0 ? 1 : 0);
  L.lit(" total_count="); L.dec(n);
  L.lit(" nonzero_count="); L.dec(nz);
  L.lit(" ts_sec="); L.dec((long long)ts.tv_sec);
  L.lit(" ts_ns="); L.dec((long long)ts.tv_nsec);
  L.lit("\n");
  sigchain_probe::write_line(L);
}

// l3_trampoline_entry: 手写 aarch64 汇编，逐字节重放被 16 字节 far-branch
// stub 覆盖的 art::Thread::artImplicitSuspendFromCode 前 4 条指令
// （stp x29,x30,[sp,#-32]! / stp x20,x19,[sp,#16] / mov x29,sp /
// ldr w8,[x0]），随后调用 l3_probe_record(flags) 做只读计数/日志，最后跳回
// 原函数 tst 指令之前的位置（g_l3_resume_addr = 被劫持地址+16）继续正常
// 执行——真正的 tst/b.ne 尚未运行，NZCV 从未被本 trampoline 观察或依赖，
// 故不需要 mrs/msr 显式保存恢复（这正是 route②recipe 建议的"不破坏控制流
// 的等价 trampoline"，不是另一套设计）。x0（self 指针）和 w8（flags，供
// 原始 tst 使用）在调用 l3_probe_record 前后显式 stp/ldp 保护，因为 AAPCS
// 下 x0/x8 都不是 callee-saved，一次 `bl` 有权限清空它们。
//
// x30(LR) 说明（codex round1 阻断性意见，已核实+加固）：被重放的
// `stp x29,x30,[sp,#-32]!` 已经把"进入本函数时的原始 LR"存进了栈；原函数
// 自己的 epilogue（部署版 0x7fd7fc 的 `ldp x29,x30,[sp],#32`）是从**栈**
// 读回 x30，不是从寄存器——已用 llvm-objdump 逐指令核对过原函数从
// resume 点（target+0x10）到该 epilogue 之间没有任何指令直接读取 x30
// 寄存器（只用到 x0/x1/x2/x3/x4/x5/x8/x9/x19/x20），所以我们的
// `bl l3_probe_record` 清空 x30 寄存器本身不影响正确性。即便如此，仍显式
// 多做一次 x30 save/restore（额外 2 条指令，栈仍 16 字节对齐）作为纵深
// 防御，不依赖这条"读了完整反汇编才能下的结论"在未来任何情况下都成立。
__asm__(
    ".text\n"
    ".align 4\n"
    ".global l3_trampoline_entry\n"
    "l3_trampoline_entry:\n"
    "  stp x29, x30, [sp, #-32]!\n"   // 重放原指令 1
    "  stp x20, x19, [sp, #16]\n"     // 重放原指令 2
    "  mov x29, sp\n"                 // 重放原指令 3
    "  ldr w8, [x0]\n"                // 重放原指令 4（flags -> w8）
    "  stp x0, x8, [sp, #-32]!\n"     // 保护 x0(self)/w8(flags) 跨 bl
    "  str x30, [sp, #16]\n"          // 纵深防御：额外显式保护 x30
    "  mov w0, w8\n"                  // arg0 = flags
    "  bl l3_probe_record\n"
    "  ldr x30, [sp, #16]\n"          // 恢复 x30
    "  ldp x0, x8, [sp], #32\n"       // 恢复 x0/w8
    "  adrp x9, g_l3_resume_addr\n"
    "  add x9, x9, :lo12:g_l3_resume_addr\n"
    "  ldr x9, [x9]\n"                // x9 = 原函数 tst 指令地址
    "  br x9\n"
);

#endif  // SIGCHAIN_PROBE_LOG

// ---------------------------------------------------------------------------
// AOSP 导出符号实现（转发到 musl）。
// 注意: extern "C" 给出 unmangled 符号名（与 namespace 无关），与 libart 的
// weak undef `AddSpecialSignalHandlerFn` 等精确匹配。默认 visibility → 导出。
// ---------------------------------------------------------------------------
extern "C" {

// ART FaultManager::Init → AddSpecialSignalHandlerFn(SIGSEGV, &sa)
// （userfaultfd GC 时另注册 SIGBUS）。转译结构字段后落 musl chain slot 0。
void AddSpecialSignalHandlerFn(int signo, art::SigchainAction* sa) {
  struct signal_chain_action m;
#ifdef SIGCHAIN_PROBE_LOG
  sigchain_probe::log_register(signo, sa->sc_flags);
  if (signo >= 0 && signo < 64) {
    sigchain_probe::g_real_handler[signo] = sa->sc_sigaction;
  }
  m.sca_sigaction = sigchain_probe::probe_thunk;  // 代理：记调用+转发，行为不变
  // v6 L3：复用这个已证明安全的非信号上下文（FaultManager::Init 首次调用）
  // 安装 artImplicitSuspendFromCode 入口 patch；内部有 g_l3_patch_installed
  // 幂等保护，SIGSEGV/SIGBUS 两次注册只真正安装一次。
  sigchain_probe::l3_install_patch();
#else
  m.sca_sigaction = sa->sc_sigaction;   // bool(*)(int,siginfo_t*,void*) — 同型
#endif
  m.sca_mask      = sa->sc_mask;        // sigset_t — 同型
  // sc_flags(uint64) → sca_flags(int)：唯一使用位 SIGCHAIN_ALLOW_NORETURN=0x1，
  // 安全收窄；两边语义一致。
  m.sca_flags     = static_cast<int>(sa->sc_flags & 0xffffffffULL);
  add_special_signal_handler(signo, &m);
}

// ART FaultManager::Release → RemoveSpecialSignalHandlerFn(signo, fn)
void RemoveSpecialSignalHandlerFn(int signo, bool (*fn)(int, siginfo_t*, void*)) {
  remove_special_signal_handler(signo, fn);
}

// EnsureFrontOfChain: AOSP 私有 registry 用它把自己重置到内核前端。musl 是统一
// chain，内核前端恒为 musl signal_chain_handler（mark 时已装），无独立 front 概念，
// 故 no-op。残留风险（已标注）: 若某非-sigchain-aware 库直接 __libc_sigaction
// 抢占（ART 路径不会），本垫片不再纠正——交由 musl 统一管理。
void EnsureFrontOfChain(int /*signo*/) {
  // no-op: musl 统一 chain 自持内核前端。
}

// SkipAddSignalHandler: AOSP 用它在 debuggable runtime 关闭自带 sigaction 拦截器。
// 本垫片无 sigaction 拦截器（musl 内建 intercept_sigaction 独立处理），故 no-op。
void SkipAddSignalHandler(bool /*value*/) {
  // no-op: 本垫片不拦截 sigaction，musl 自管。
}

}  // extern "C"
