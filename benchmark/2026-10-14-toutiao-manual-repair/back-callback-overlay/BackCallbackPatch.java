import java.util.*;
import org.jf.dexlib2.*;
import org.jf.dexlib2.iface.*;
import org.jf.dexlib2.immutable.*;
import org.jf.dexlib2.immutable.reference.*;
import org.jf.dexlib2.builder.*;
import org.jf.dexlib2.builder.instruction.*;
import org.jf.dexlib2.rewriter.*;

/** Exact-input single-method transformation. No Android/device execution. */
public final class BackCallbackPatch {
  static final String OWNER = "Ladapter/activity/ActivityClientControllerAdapter;";
  static final String CB = "Landroid/app/IRequestFinishCallback;";
  static final List<String> PARAMS = Arrays.asList("Landroid/os/IBinder;", CB);
  static boolean target(Method m) {
    return OWNER.equals(m.getDefiningClass()) && "onBackPressed".equals(m.getName())
      && PARAMS.equals(m.getParameterTypes()) && "V".equals(m.getReturnType());
  }
  static ImmutableMethodReference ref(String cls, String name, String ret, String... args) {
    return new ImmutableMethodReference(cls, name, Arrays.asList(args), ret);
  }
  static MethodImplementation body() {
    // v0 tag, v1 message, p0=v2, p1=v3(token), p2=v4(callback).
    MethodImplementationBuilder b = new MethodImplementationBuilder(5);
    b.addInstruction(new BuilderInstruction21c(Opcode.CONST_STRING,0,new ImmutableStringReference("OH_ACCAdapter")));
    b.addInstruction(new BuilderInstruction21c(Opcode.CONST_STRING,1,new ImmutableStringReference("[BACK51] onBackPressed callback entry")));
    b.addInstruction(new BuilderInstruction35c(Opcode.INVOKE_STATIC,2,0,1,0,0,0,ref("Landroid/util/Log;","i","I","Ljava/lang/String;","Ljava/lang/String;")));
    b.addInstruction(new BuilderInstruction21t(Opcode.IF_EQZ,4,b.getLabel("done")));
    b.addLabel("start");
    b.addInstruction(new BuilderInstruction35c(Opcode.INVOKE_INTERFACE,1,4,0,0,0,0,ref(CB,"requestFinish","V")));
    b.addLabel("end");
    b.addInstruction(new BuilderInstruction21c(Opcode.CONST_STRING,1,new ImmutableStringReference("[BACK51] requestFinish returned; UI acceptance pending")));
    b.addInstruction(new BuilderInstruction35c(Opcode.INVOKE_STATIC,2,0,1,0,0,0,ref("Landroid/util/Log;","i","I","Ljava/lang/String;","Ljava/lang/String;")));
    b.addInstruction(new BuilderInstruction10t(Opcode.GOTO,b.getLabel("done")));
    b.addLabel("error");
    b.addInstruction(new BuilderInstruction11x(Opcode.MOVE_EXCEPTION,2));
    b.addInstruction(new BuilderInstruction21c(Opcode.CONST_STRING,1,new ImmutableStringReference("[BACK51] requestFinish RemoteException")));
    b.addInstruction(new BuilderInstruction35c(Opcode.INVOKE_STATIC,3,0,1,2,0,0,ref("Landroid/util/Log;","e","I","Ljava/lang/String;","Ljava/lang/String;","Ljava/lang/Throwable;")));
    b.addLabel("done");
    b.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
    b.addCatch("Landroid/os/RemoteException;",b.getLabel("start"),b.getLabel("end"),b.getLabel("error"));
    return b.getMethodImplementation();
  }
  public static void main(String[] args) throws Exception {
    DexFile input = DexFileFactory.loadDexFile(args[0], Opcodes.getDefault());
    int count=0;
    for(ClassDef c:input.getClasses()) for(Method m:c.getMethods()) if(target(m)) {
      count++;
      List<org.jf.dexlib2.iface.instruction.Instruction> ins = new ArrayList<>();
      for(org.jf.dexlib2.iface.instruction.Instruction i:m.getImplementation().getInstructions()) ins.add(i);
      if(m.getImplementation().getRegisterCount()!=3 || ins.size()!=1 || ins.get(0).getOpcode()!=Opcode.RETURN_VOID)
        throw new IllegalArgumentException("REFUSE: not exact empty callback");
    }
    if(count!=1) throw new IllegalArgumentException("REFUSE: target count="+count);
    DexRewriter r = new DexRewriter(new RewriterModule() {
      public Rewriter<Method> getMethodRewriter(Rewriters rw) {
        return m -> target(m) ? new ImmutableMethod(m.getDefiningClass(),m.getName(),m.getParameters(),m.getReturnType(),m.getAccessFlags(),m.getAnnotations(),m.getHiddenApiRestrictions(),body()) : m;
      }
    });
    DexFileFactory.writeDexFile(args[1],r.getDexFileRewriter().rewrite(input));
    System.out.println("BACK51 exact empty callback replaced; all other definitions retained");
  }
}
