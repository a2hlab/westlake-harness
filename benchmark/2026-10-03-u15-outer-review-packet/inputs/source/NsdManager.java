/*
 * Copyright (C) 2021 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package android.net.nsd;

import android.annotation.IntDef;
import android.annotation.NonNull;
import android.annotation.SdkConstant;
import android.annotation.SdkConstant.SdkConstantType;

import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;

/**
 * Route-A minimal android.net.nsd.NsdManager (U15 stubs). Every member below that exists in AOSP is copied verbatim
 * from AOSP android-14.0.0_r1 packages/modules/Connectivity bd692130
 * framework-t/src/android/net/nsd/NsdManager.java (sha256 6e30cf2e): the public constants (lines 140-172, 250-251,
 * 660-693), the two failure-code annotation types (695-710) and the DiscoveryListener / RegistrationListener /
 * ResolveListener interfaces (712-783). The rest of the AOSP class (binder client, executors, ServiceInfoCallback)
 * is not present. Route A registers no NSD service, so Context.getSystemService(NSD_SERVICE) returns null exactly
 * as AOSP does when the NSD binder is absent (SystemServiceRegistry: no fetcher / ServiceNotFoundException -> null),
 * and no NsdManager instance can exist: the AOSP constructor is @hide and absent here. The five public methods apps
 * link against are kept with their AOSP 14 signatures so callers verify; they are unreachable without an instance.
 */
public final class NsdManager {
    /**
     * Broadcast intent action to indicate whether network service discovery is
     * enabled or disabled. An extra {@link #EXTRA_NSD_STATE} provides the state
     * information as int.
     *
     * @see #EXTRA_NSD_STATE
     */
    @SdkConstant(SdkConstantType.BROADCAST_INTENT_ACTION)
    public static final String ACTION_NSD_STATE_CHANGED = "android.net.nsd.STATE_CHANGED";

    /**
     * The lookup key for an int that indicates whether network service discovery is enabled
     * or disabled. Retrieve it with {@link android.content.Intent#getIntExtra(String,int)}.
     *
     * @see #NSD_STATE_DISABLED
     * @see #NSD_STATE_ENABLED
     */
    public static final String EXTRA_NSD_STATE = "nsd_state";

    /**
     * Network service discovery is disabled
     *
     * @see #ACTION_NSD_STATE_CHANGED
     */
    // TODO: Deprecate this since NSD service is never disabled.
    public static final int NSD_STATE_DISABLED = 1;

    /**
     * Network service discovery is enabled
     *
     * @see #ACTION_NSD_STATE_CHANGED
     */
    public static final int NSD_STATE_ENABLED = 2;

    /** Dns based service discovery protocol */
    public static final int PROTOCOL_DNS_SD = 0x0001;

    /**
     * Failures are passed with {@link RegistrationListener#onRegistrationFailed},
     * {@link RegistrationListener#onUnregistrationFailed},
     * {@link DiscoveryListener#onStartDiscoveryFailed},
     * {@link DiscoveryListener#onStopDiscoveryFailed} or {@link ResolveListener#onResolveFailed}.
     *
     * Indicates that the operation failed due to an internal error.
     */
    public static final int FAILURE_INTERNAL_ERROR               = 0;

    /**
     * Indicates that the operation failed because it is already active.
     */
    public static final int FAILURE_ALREADY_ACTIVE              = 3;

    /**
     * Indicates that the operation failed because the maximum outstanding
     * requests from the applications have reached.
     */
    public static final int FAILURE_MAX_LIMIT                   = 4;

    /**
     * Indicates that the stop operation failed because it is not running.
     * This failure is passed with {@link ResolveListener#onStopResolutionFailed}.
     */
    public static final int FAILURE_OPERATION_NOT_RUNNING       = 5;

    /**
     * Indicates that the service has failed to resolve because of bad parameters.
     *
     * This failure is passed with
     * {@link ServiceInfoCallback#onServiceInfoCallbackRegistrationFailed}.
     */
    public static final int FAILURE_BAD_PARAMETERS              = 6;

    /** @hide */
    @Retention(RetentionPolicy.SOURCE)
    @IntDef(value = {
            FAILURE_OPERATION_NOT_RUNNING,
    })
    public @interface StopOperationFailureCode {
    }

    /** @hide */
    @Retention(RetentionPolicy.SOURCE)
    @IntDef(value = {
            FAILURE_ALREADY_ACTIVE,
            FAILURE_BAD_PARAMETERS,
    })
    public @interface ResolutionFailureCode {
    }

    /** Interface for callback invocation for service discovery */
    public interface DiscoveryListener {

        public void onStartDiscoveryFailed(String serviceType, int errorCode);

        public void onStopDiscoveryFailed(String serviceType, int errorCode);

        public void onDiscoveryStarted(String serviceType);

        public void onDiscoveryStopped(String serviceType);

        public void onServiceFound(NsdServiceInfo serviceInfo);

        public void onServiceLost(NsdServiceInfo serviceInfo);
    }

    /** Interface for callback invocation for service registration */
    public interface RegistrationListener {

        public void onRegistrationFailed(NsdServiceInfo serviceInfo, int errorCode);

        public void onUnregistrationFailed(NsdServiceInfo serviceInfo, int errorCode);

        public void onServiceRegistered(NsdServiceInfo serviceInfo);

        public void onServiceUnregistered(NsdServiceInfo serviceInfo);
    }

    /**
     * Callback for use with {@link NsdManager#resolveService} to resolve the service info and use
     * with {@link NsdManager#stopServiceResolution} to stop resolution.
     */
    public interface ResolveListener {

        /**
         * Called on the internal thread or with an executor passed to
         * {@link NsdManager#resolveService} to report the resolution was failed with an error.
         *
         * A resolution operation would call either onServiceResolved or onResolveFailed once based
         * on the result.
         */
        void onResolveFailed(NsdServiceInfo serviceInfo, int errorCode);

        /**
         * Called on the internal thread or with an executor passed to
         * {@link NsdManager#resolveService} to report the resolved service info.
         *
         * A resolution operation would call either onServiceResolved or onResolveFailed once based
         * on the result.
         */
        void onServiceResolved(NsdServiceInfo serviceInfo);

        /**
         * Called on the internal thread or with an executor passed to
         * {@link NsdManager#resolveService} to report the resolution was stopped.
         *
         * A stop resolution operation would call either onResolutionStopped or
         * onStopResolutionFailed once based on the result.
         */
        default void onResolutionStopped(@NonNull NsdServiceInfo serviceInfo) { }

        /**
         * Called once on the internal thread or with an executor passed to
         * {@link NsdManager#resolveService} to report that stopping resolution failed with an
         * error.
         *
         * A stop resolution operation would call either onResolutionStopped or
         * onStopResolutionFailed once based on the result.
         */
        default void onStopResolutionFailed(@NonNull NsdServiceInfo serviceInfo,
                @StopOperationFailureCode int errorCode) { }
    }

    private NsdManager() {
    }

    /** AOSP 14 signature; unreachable on route A (no instance). */
    public void registerService(NsdServiceInfo serviceInfo, int protocolType,
            RegistrationListener listener) {
        throw new UnsupportedOperationException("NSD service is not available");
    }

    /** AOSP 14 signature; unreachable on route A (no instance). */
    public void unregisterService(RegistrationListener listener) {
        throw new UnsupportedOperationException("NSD service is not available");
    }

    /** AOSP 14 signature; unreachable on route A (no instance). */
    public void discoverServices(String serviceType, int protocolType, DiscoveryListener listener) {
        throw new UnsupportedOperationException("NSD service is not available");
    }

    /** AOSP 14 signature; unreachable on route A (no instance). */
    public void stopServiceDiscovery(DiscoveryListener listener) {
        throw new UnsupportedOperationException("NSD service is not available");
    }

    /** AOSP 14 signature; unreachable on route A (no instance). */
    public void resolveService(NsdServiceInfo serviceInfo, ResolveListener listener) {
        throw new UnsupportedOperationException("NSD service is not available");
    }
}
