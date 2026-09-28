/*
 * ServiceBindingCoordinator.java
 *
 * Fn07.A01 的 host 可测绑定编排器。它把“注册记录—调用 OH—按结果提交或
 * 回滚”收敛为一个串行事务，避免 ActivityManagerAdapter 中散落的回滚逻辑
 * 误删既有连接。
 */
package adapter.activity;

import android.app.IServiceConnection;
import android.content.ComponentName;
import android.util.Log;

public final class ServiceBindingCoordinator {

    private static final String TAG = "OH_SvcBindCoordinator";
    private static final int RESULT_OK = 0;
    private static final int RESULT_FAILED = 0;
    private static final int RESULT_BOUND = 1;

    /** 产品侧由 nativeConnectAbility 实现；host 测试注入确定性替身。 */
    public interface NativeAbilityGateway {
        int connect(String bundleName, String abilityName, int connectionId);
        boolean consumeConnectionFailure(int connectionId);
    }

    private final ServiceConnectionRegistry registry;
    private final NativeAbilityGateway gateway;

    public ServiceBindingCoordinator(
            ServiceConnectionRegistry registry, NativeAbilityGateway gateway) {
        if (registry == null || gateway == null) {
            throw new IllegalArgumentException("registry/gateway must not be null");
        }
        this.registry = registry;
        this.gateway = gateway;
    }

    /**
     * 串行执行单次绑定事务。
     *
     * 同一 connection 的重复 bind 在既有事务完成后才可见；若记录已存在，
     * 直接返回成功且不再次调用 OH。新记录只有在 OH 返回 ERR_OK(0) 时提交；
     * 任意非零返回或 RuntimeException 都按预期 connId compare-and-remove。
     */
    public synchronized int bind(
            IServiceConnection connection,
            ComponentName target,
            String bundleName,
            String abilityName) {
        if (connection == null || target == null
                || bundleName == null || abilityName == null
                || bundleName.isEmpty() || abilityName.isEmpty()) {
            Log.w(TAG, "bind: invalid connection or explicit service identity");
            return RESULT_FAILED;
        }

        ServiceConnectionRegistry.RegistrationResult registration =
                registry.registerConnection(connection, target);
        if (!registration.created) {
            if (!gateway.consumeConnectionFailure(registration.connectionId)) {
                return RESULT_BOUND;
            }

            // OH 已异步失败但 JNI 未能通知 Java：只移除仍指向失败 connId
            // 的陈旧记录。若期间已由其他事务替换，当前记录不属于该失败。
            if (!registry.unregisterConnection(
                    connection, registration.connectionId)) {
                return RESULT_BOUND;
            }
            registration = registry.registerConnection(connection, target);
            if (!registration.created) {
                return RESULT_BOUND;
            }
        }

        final int nativeResult;
        try {
            nativeResult = gateway.connect(
                    bundleName, abilityName, registration.connectionId);
        } catch (RuntimeException error) {
            registry.unregisterConnection(connection, registration.connectionId);
            Log.e(TAG, "bind: native gateway threw, rolled back connId="
                    + registration.connectionId, error);
            return RESULT_FAILED;
        }

        if (nativeResult != RESULT_OK) {
            registry.unregisterConnection(connection, registration.connectionId);
            Log.w(TAG, "bind: ConnectAbility rejected, rc=" + nativeResult
                    + " connId=" + registration.connectionId);
            return RESULT_FAILED;
        }
        return RESULT_BOUND;
    }
}
