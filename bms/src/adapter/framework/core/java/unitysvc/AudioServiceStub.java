package adapter.core.unitysvc;

/**
 * [UNITY-SVC-STUB] Auto-generated safe-default stub extending android.media.IAudioService.Stub.
 * Generated 2026-07-11 from AOSP javap signatures (framework-minus-apex turbine).
 * Non-void methods return null/0/false per adapter DisplayManagerAdapter template.
 */
public final class AudioServiceStub extends android.media.IAudioService.Stub {
    @Override public int trackPlayer(android.media.PlayerBase.PlayerIdCard p0) throws android.os.RemoteException { return 0; }
    @Override public void playerAttributes(int p0, android.media.AudioAttributes p1) throws android.os.RemoteException {}
    @Override public void playerEvent(int p0, int p1, int p2) throws android.os.RemoteException {}
    @Override public void releasePlayer(int p0) throws android.os.RemoteException {}
    @Override public int trackRecorder(android.os.IBinder p0) throws android.os.RemoteException { return 0; }
    @Override public void recorderEvent(int p0, int p1) throws android.os.RemoteException {}
    @Override public void releaseRecorder(int p0) throws android.os.RemoteException {}
    @Override public void playerSessionId(int p0, int p1) throws android.os.RemoteException {}
    @Override public void portEvent(int p0, int p1, android.os.PersistableBundle p2) throws android.os.RemoteException {}
    @Override public void adjustStreamVolume(int p0, int p1, int p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public void adjustStreamVolumeWithAttribution(int p0, int p1, int p2, java.lang.String p3, java.lang.String p4) throws android.os.RemoteException {}
    @Override public void setStreamVolume(int p0, int p1, int p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public void setStreamVolumeWithAttribution(int p0, int p1, int p2, java.lang.String p3, java.lang.String p4) throws android.os.RemoteException {}
    @Override public void setDeviceVolume(android.media.VolumeInfo p0, android.media.AudioDeviceAttributes p1, java.lang.String p2) throws android.os.RemoteException {}
    @Override public android.media.VolumeInfo getDeviceVolume(android.media.VolumeInfo p0, android.media.AudioDeviceAttributes p1, java.lang.String p2) throws android.os.RemoteException { return null; }
    @Override public void handleVolumeKey(android.view.KeyEvent p0, boolean p1, java.lang.String p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public boolean isStreamMute(int p0) throws android.os.RemoteException { return false; }
    @Override public void forceRemoteSubmixFullVolume(boolean p0, android.os.IBinder p1) throws android.os.RemoteException {}
    @Override public boolean isMasterMute() throws android.os.RemoteException { return false; }
    @Override public void setMasterMute(boolean p0, int p1, java.lang.String p2, int p3, java.lang.String p4) throws android.os.RemoteException {}
    @Override public int getStreamVolume(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getStreamMinVolume(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getStreamMaxVolume(int p0) throws android.os.RemoteException { return 0; }
    @Override public java.util.List<android.media.audiopolicy.AudioVolumeGroup> getAudioVolumeGroups() throws android.os.RemoteException { return null; }
    @Override public void setVolumeGroupVolumeIndex(int p0, int p1, int p2, java.lang.String p3, java.lang.String p4) throws android.os.RemoteException {}
    @Override public int getVolumeGroupVolumeIndex(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getVolumeGroupMaxVolumeIndex(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getVolumeGroupMinVolumeIndex(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getLastAudibleVolumeForVolumeGroup(int p0) throws android.os.RemoteException { return 0; }
    @Override public boolean isVolumeGroupMuted(int p0) throws android.os.RemoteException { return false; }
    @Override public void adjustVolumeGroupVolume(int p0, int p1, int p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public int getLastAudibleStreamVolume(int p0) throws android.os.RemoteException { return 0; }
    @Override public void setSupportedSystemUsages(int[] p0) throws android.os.RemoteException {}
    @Override public int[] getSupportedSystemUsages() throws android.os.RemoteException { return null; }
    @Override public java.util.List<android.media.audiopolicy.AudioProductStrategy> getAudioProductStrategies() throws android.os.RemoteException { return null; }
    @Override public boolean isMicrophoneMuted() throws android.os.RemoteException { return false; }
    @Override public boolean isUltrasoundSupported() throws android.os.RemoteException { return false; }
    @Override public boolean isHotwordStreamSupported(boolean p0) throws android.os.RemoteException { return false; }
    @Override public void setMicrophoneMute(boolean p0, java.lang.String p1, int p2, java.lang.String p3) throws android.os.RemoteException {}
    @Override public void setMicrophoneMuteFromSwitch(boolean p0) throws android.os.RemoteException {}
    @Override public void setRingerModeExternal(int p0, java.lang.String p1) throws android.os.RemoteException {}
    @Override public void setRingerModeInternal(int p0, java.lang.String p1) throws android.os.RemoteException {}
    @Override public int getRingerModeExternal() throws android.os.RemoteException { return 0; }
    @Override public int getRingerModeInternal() throws android.os.RemoteException { return 0; }
    @Override public boolean isValidRingerMode(int p0) throws android.os.RemoteException { return false; }
    @Override public void setVibrateSetting(int p0, int p1) throws android.os.RemoteException {}
    @Override public int getVibrateSetting(int p0) throws android.os.RemoteException { return 0; }
    @Override public boolean shouldVibrate(int p0) throws android.os.RemoteException { return false; }
    @Override public void setMode(int p0, android.os.IBinder p1, java.lang.String p2) throws android.os.RemoteException {}
    @Override public int getMode() throws android.os.RemoteException { return 0; }
    @Override public void playSoundEffect(int p0, int p1) throws android.os.RemoteException {}
    @Override public void playSoundEffectVolume(int p0, float p1) throws android.os.RemoteException {}
    @Override public boolean loadSoundEffects() throws android.os.RemoteException { return false; }
    @Override public void unloadSoundEffects() throws android.os.RemoteException {}
    @Override public void reloadAudioSettings() throws android.os.RemoteException {}
    @Override public java.util.Map getSurroundFormats() throws android.os.RemoteException { return null; }
    @Override public java.util.List getReportedSurroundFormats() throws android.os.RemoteException { return null; }
    @Override public boolean setSurroundFormatEnabled(int p0, boolean p1) throws android.os.RemoteException { return false; }
    @Override public boolean isSurroundFormatEnabled(int p0) throws android.os.RemoteException { return false; }
    @Override public boolean setEncodedSurroundMode(int p0) throws android.os.RemoteException { return false; }
    @Override public int getEncodedSurroundMode(int p0) throws android.os.RemoteException { return 0; }
    @Override public void setSpeakerphoneOn(android.os.IBinder p0, boolean p1) throws android.os.RemoteException {}
    @Override public boolean isSpeakerphoneOn() throws android.os.RemoteException { return false; }
    @Override public void setBluetoothScoOn(boolean p0) throws android.os.RemoteException {}
    @Override public void setA2dpSuspended(boolean p0) throws android.os.RemoteException {}
    @Override public void setLeAudioSuspended(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isBluetoothScoOn() throws android.os.RemoteException { return false; }
    @Override public void setBluetoothA2dpOn(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isBluetoothA2dpOn() throws android.os.RemoteException { return false; }
    @Override public int requestAudioFocus(android.media.AudioAttributes p0, int p1, android.os.IBinder p2, android.media.IAudioFocusDispatcher p3, java.lang.String p4, java.lang.String p5, java.lang.String p6, int p7, android.media.audiopolicy.IAudioPolicyCallback p8, int p9) throws android.os.RemoteException { return 0; }
    @Override public int abandonAudioFocus(android.media.IAudioFocusDispatcher p0, java.lang.String p1, android.media.AudioAttributes p2, java.lang.String p3) throws android.os.RemoteException { return 0; }
    @Override public void unregisterAudioFocusClient(java.lang.String p0) throws android.os.RemoteException {}
    @Override public int getCurrentAudioFocus() throws android.os.RemoteException { return 0; }
    @Override public void startBluetoothSco(android.os.IBinder p0, int p1) throws android.os.RemoteException {}
    @Override public void startBluetoothScoVirtualCall(android.os.IBinder p0) throws android.os.RemoteException {}
    @Override public void stopBluetoothSco(android.os.IBinder p0) throws android.os.RemoteException {}
    @Override public void forceVolumeControlStream(int p0, android.os.IBinder p1) throws android.os.RemoteException {}
    @Override public void setRingtonePlayer(android.media.IRingtonePlayer p0) throws android.os.RemoteException {}
    @Override public android.media.IRingtonePlayer getRingtonePlayer() throws android.os.RemoteException { return null; }
    @Override public int getUiSoundsStreamType() throws android.os.RemoteException { return 0; }
    @Override public java.util.List getIndependentStreamTypes() throws android.os.RemoteException { return null; }
    @Override public int getStreamTypeAlias(int p0) throws android.os.RemoteException { return 0; }
    @Override public boolean isVolumeControlUsingVolumeGroups() throws android.os.RemoteException { return false; }
    @Override public void registerStreamAliasingDispatcher(android.media.IStreamAliasingDispatcher p0, boolean p1) throws android.os.RemoteException {}
    @Override public void setNotifAliasRingForTest(boolean p0) throws android.os.RemoteException {}
    @Override public void setWiredDeviceConnectionState(android.media.AudioDeviceAttributes p0, int p1, java.lang.String p2) throws android.os.RemoteException {}
    @Override public android.media.AudioRoutesInfo startWatchingRoutes(android.media.IAudioRoutesObserver p0) throws android.os.RemoteException { return null; }
    @Override public boolean isCameraSoundForced() throws android.os.RemoteException { return false; }
    @Override public void setVolumeController(android.media.IVolumeController p0) throws android.os.RemoteException {}
    @Override public android.media.IVolumeController getVolumeController() throws android.os.RemoteException { return null; }
    @Override public void notifyVolumeControllerVisible(android.media.IVolumeController p0, boolean p1) throws android.os.RemoteException {}
    @Override public boolean isStreamAffectedByRingerMode(int p0) throws android.os.RemoteException { return false; }
    @Override public boolean isStreamAffectedByMute(int p0) throws android.os.RemoteException { return false; }
    @Override public void disableSafeMediaVolume(java.lang.String p0) throws android.os.RemoteException {}
    @Override public void lowerVolumeToRs1(java.lang.String p0) throws android.os.RemoteException {}
    @Override public float getOutputRs2UpperBound() throws android.os.RemoteException { return 0f; }
    @Override public void setOutputRs2UpperBound(float p0) throws android.os.RemoteException {}
    @Override public float getCsd() throws android.os.RemoteException { return 0f; }
    @Override public void setCsd(float p0) throws android.os.RemoteException {}
    @Override public void forceUseFrameworkMel(boolean p0) throws android.os.RemoteException {}
    @Override public void forceComputeCsdOnAllDevices(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isCsdEnabled() throws android.os.RemoteException { return false; }
    @Override public int setHdmiSystemAudioSupported(boolean p0) throws android.os.RemoteException { return 0; }
    @Override public boolean isHdmiSystemAudioSupported() throws android.os.RemoteException { return false; }
    @Override public java.lang.String registerAudioPolicy(android.media.audiopolicy.AudioPolicyConfig p0, android.media.audiopolicy.IAudioPolicyCallback p1, boolean p2, boolean p3, boolean p4, boolean p5, android.media.projection.IMediaProjection p6) throws android.os.RemoteException { return null; }
    @Override public void unregisterAudioPolicyAsync(android.media.audiopolicy.IAudioPolicyCallback p0) throws android.os.RemoteException {}
    @Override public void unregisterAudioPolicy(android.media.audiopolicy.IAudioPolicyCallback p0) throws android.os.RemoteException {}
    @Override public int addMixForPolicy(android.media.audiopolicy.AudioPolicyConfig p0, android.media.audiopolicy.IAudioPolicyCallback p1) throws android.os.RemoteException { return 0; }
    @Override public int removeMixForPolicy(android.media.audiopolicy.AudioPolicyConfig p0, android.media.audiopolicy.IAudioPolicyCallback p1) throws android.os.RemoteException { return 0; }
    @Override public int setFocusPropertiesForPolicy(int p0, android.media.audiopolicy.IAudioPolicyCallback p1) throws android.os.RemoteException { return 0; }
    @Override public void setVolumePolicy(android.media.VolumePolicy p0) throws android.os.RemoteException {}
    @Override public boolean hasRegisteredDynamicPolicy() throws android.os.RemoteException { return false; }
    @Override public void registerRecordingCallback(android.media.IRecordingConfigDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterRecordingCallback(android.media.IRecordingConfigDispatcher p0) throws android.os.RemoteException {}
    @Override public java.util.List<android.media.AudioRecordingConfiguration> getActiveRecordingConfigurations() throws android.os.RemoteException { return null; }
    @Override public void registerPlaybackCallback(android.media.IPlaybackConfigDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterPlaybackCallback(android.media.IPlaybackConfigDispatcher p0) throws android.os.RemoteException {}
    @Override public java.util.List<android.media.AudioPlaybackConfiguration> getActivePlaybackConfigurations() throws android.os.RemoteException { return null; }
    @Override public int getFocusRampTimeMs(int p0, android.media.AudioAttributes p1) throws android.os.RemoteException { return 0; }
    @Override public int dispatchFocusChange(android.media.AudioFocusInfo p0, int p1, android.media.audiopolicy.IAudioPolicyCallback p2) throws android.os.RemoteException { return 0; }
    @Override public void playerHasOpPlayAudio(int p0, boolean p1) throws android.os.RemoteException {}
    @Override public void handleBluetoothActiveDeviceChanged(android.bluetooth.BluetoothDevice p0, android.bluetooth.BluetoothDevice p1, android.media.BluetoothProfileConnectionInfo p2) throws android.os.RemoteException {}
    @Override public void setFocusRequestResultFromExtPolicy(android.media.AudioFocusInfo p0, int p1, android.media.audiopolicy.IAudioPolicyCallback p2) throws android.os.RemoteException {}
    @Override public void registerAudioServerStateDispatcher(android.media.IAudioServerStateDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterAudioServerStateDispatcher(android.media.IAudioServerStateDispatcher p0) throws android.os.RemoteException {}
    @Override public boolean isAudioServerRunning() throws android.os.RemoteException { return false; }
    @Override public int setUidDeviceAffinity(android.media.audiopolicy.IAudioPolicyCallback p0, int p1, int[] p2, java.lang.String[] p3) throws android.os.RemoteException { return 0; }
    @Override public int removeUidDeviceAffinity(android.media.audiopolicy.IAudioPolicyCallback p0, int p1) throws android.os.RemoteException { return 0; }
    @Override public int setUserIdDeviceAffinity(android.media.audiopolicy.IAudioPolicyCallback p0, int p1, int[] p2, java.lang.String[] p3) throws android.os.RemoteException { return 0; }
    @Override public int removeUserIdDeviceAffinity(android.media.audiopolicy.IAudioPolicyCallback p0, int p1) throws android.os.RemoteException { return 0; }
    @Override public boolean hasHapticChannels(android.net.Uri p0) throws android.os.RemoteException { return false; }
    @Override public boolean isCallScreeningModeSupported() throws android.os.RemoteException { return false; }
    @Override public int setPreferredDevicesForStrategy(int p0, java.util.List<android.media.AudioDeviceAttributes> p1) throws android.os.RemoteException { return 0; }
    @Override public int removePreferredDevicesForStrategy(int p0) throws android.os.RemoteException { return 0; }
    @Override public java.util.List<android.media.AudioDeviceAttributes> getPreferredDevicesForStrategy(int p0) throws android.os.RemoteException { return null; }
    @Override public int setDeviceAsNonDefaultForStrategy(int p0, android.media.AudioDeviceAttributes p1) throws android.os.RemoteException { return 0; }
    @Override public int removeDeviceAsNonDefaultForStrategy(int p0, android.media.AudioDeviceAttributes p1) throws android.os.RemoteException { return 0; }
    @Override public java.util.List<android.media.AudioDeviceAttributes> getNonDefaultDevicesForStrategy(int p0) throws android.os.RemoteException { return null; }
    @Override public java.util.List<android.media.AudioDeviceAttributes> getDevicesForAttributes(android.media.AudioAttributes p0) throws android.os.RemoteException { return null; }
    @Override public java.util.List<android.media.AudioDeviceAttributes> getDevicesForAttributesUnprotected(android.media.AudioAttributes p0) throws android.os.RemoteException { return null; }
    @Override public void addOnDevicesForAttributesChangedListener(android.media.AudioAttributes p0, android.media.IDevicesForAttributesCallback p1) throws android.os.RemoteException {}
    @Override public void removeOnDevicesForAttributesChangedListener(android.media.IDevicesForAttributesCallback p0) throws android.os.RemoteException {}
    @Override public int setAllowedCapturePolicy(int p0) throws android.os.RemoteException { return 0; }
    @Override public int getAllowedCapturePolicy() throws android.os.RemoteException { return 0; }
    @Override public void registerStrategyPreferredDevicesDispatcher(android.media.IStrategyPreferredDevicesDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterStrategyPreferredDevicesDispatcher(android.media.IStrategyPreferredDevicesDispatcher p0) throws android.os.RemoteException {}
    @Override public void registerStrategyNonDefaultDevicesDispatcher(android.media.IStrategyNonDefaultDevicesDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterStrategyNonDefaultDevicesDispatcher(android.media.IStrategyNonDefaultDevicesDispatcher p0) throws android.os.RemoteException {}
    @Override public void setRttEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public void setDeviceVolumeBehavior(android.media.AudioDeviceAttributes p0, int p1, java.lang.String p2) throws android.os.RemoteException {}
    @Override public int getDeviceVolumeBehavior(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return 0; }
    @Override public void setMultiAudioFocusEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public int setPreferredDevicesForCapturePreset(int p0, java.util.List<android.media.AudioDeviceAttributes> p1) throws android.os.RemoteException { return 0; }
    @Override public int clearPreferredDevicesForCapturePreset(int p0) throws android.os.RemoteException { return 0; }
    @Override public java.util.List<android.media.AudioDeviceAttributes> getPreferredDevicesForCapturePreset(int p0) throws android.os.RemoteException { return null; }
    @Override public void registerCapturePresetDevicesRoleDispatcher(android.media.ICapturePresetDevicesRoleDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterCapturePresetDevicesRoleDispatcher(android.media.ICapturePresetDevicesRoleDispatcher p0) throws android.os.RemoteException {}
    @Override public void adjustStreamVolumeForUid(int p0, int p1, int p2, java.lang.String p3, int p4, int p5, android.os.UserHandle p6, int p7) throws android.os.RemoteException {}
    @Override public void adjustSuggestedStreamVolumeForUid(int p0, int p1, int p2, java.lang.String p3, int p4, int p5, android.os.UserHandle p6, int p7) throws android.os.RemoteException {}
    @Override public void setStreamVolumeForUid(int p0, int p1, int p2, java.lang.String p3, int p4, int p5, android.os.UserHandle p6, int p7) throws android.os.RemoteException {}
    @Override public boolean isMusicActive(boolean p0) throws android.os.RemoteException { return false; }
    @Override public int getDeviceMaskForStream(int p0) throws android.os.RemoteException { return 0; }
    @Override public int[] getAvailableCommunicationDeviceIds() throws android.os.RemoteException { return null; }
    @Override public boolean setCommunicationDevice(android.os.IBinder p0, int p1) throws android.os.RemoteException { return false; }
    @Override public int getCommunicationDevice() throws android.os.RemoteException { return 0; }
    @Override public void registerCommunicationDeviceDispatcher(android.media.ICommunicationDeviceDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterCommunicationDeviceDispatcher(android.media.ICommunicationDeviceDispatcher p0) throws android.os.RemoteException {}
    @Override public boolean areNavigationRepeatSoundEffectsEnabled() throws android.os.RemoteException { return false; }
    @Override public void setNavigationRepeatSoundEffectsEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isHomeSoundEffectEnabled() throws android.os.RemoteException { return false; }
    @Override public void setHomeSoundEffectEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public boolean setAdditionalOutputDeviceDelay(android.media.AudioDeviceAttributes p0, long p1) throws android.os.RemoteException { return false; }
    @Override public long getAdditionalOutputDeviceDelay(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return 0L; }
    @Override public long getMaxAdditionalOutputDeviceDelay(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return 0L; }
    @Override public int requestAudioFocusForTest(android.media.AudioAttributes p0, int p1, android.os.IBinder p2, android.media.IAudioFocusDispatcher p3, java.lang.String p4, java.lang.String p5, int p6, int p7, int p8) throws android.os.RemoteException { return 0; }
    @Override public int abandonAudioFocusForTest(android.media.IAudioFocusDispatcher p0, java.lang.String p1, android.media.AudioAttributes p2, java.lang.String p3) throws android.os.RemoteException { return 0; }
    @Override public long getFadeOutDurationOnFocusLossMillis(android.media.AudioAttributes p0) throws android.os.RemoteException { return 0L; }
    @Override public void registerModeDispatcher(android.media.IAudioModeDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterModeDispatcher(android.media.IAudioModeDispatcher p0) throws android.os.RemoteException {}
    @Override public int getSpatializerImmersiveAudioLevel() throws android.os.RemoteException { return 0; }
    @Override public boolean isSpatializerEnabled() throws android.os.RemoteException { return false; }
    @Override public boolean isSpatializerAvailable() throws android.os.RemoteException { return false; }
    @Override public boolean isSpatializerAvailableForDevice(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return false; }
    @Override public boolean hasHeadTracker(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return false; }
    @Override public void setHeadTrackerEnabled(boolean p0, android.media.AudioDeviceAttributes p1) throws android.os.RemoteException {}
    @Override public boolean isHeadTrackerEnabled(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException { return false; }
    @Override public boolean isHeadTrackerAvailable() throws android.os.RemoteException { return false; }
    @Override public void registerSpatializerHeadTrackerAvailableCallback(android.media.ISpatializerHeadTrackerAvailableCallback p0, boolean p1) throws android.os.RemoteException {}
    @Override public void setSpatializerEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public boolean canBeSpatialized(android.media.AudioAttributes p0, android.media.AudioFormat p1) throws android.os.RemoteException { return false; }
    @Override public void registerSpatializerCallback(android.media.ISpatializerCallback p0) throws android.os.RemoteException {}
    @Override public void unregisterSpatializerCallback(android.media.ISpatializerCallback p0) throws android.os.RemoteException {}
    @Override public void registerSpatializerHeadTrackingCallback(android.media.ISpatializerHeadTrackingModeCallback p0) throws android.os.RemoteException {}
    @Override public void unregisterSpatializerHeadTrackingCallback(android.media.ISpatializerHeadTrackingModeCallback p0) throws android.os.RemoteException {}
    @Override public void registerHeadToSoundstagePoseCallback(android.media.ISpatializerHeadToSoundStagePoseCallback p0) throws android.os.RemoteException {}
    @Override public void unregisterHeadToSoundstagePoseCallback(android.media.ISpatializerHeadToSoundStagePoseCallback p0) throws android.os.RemoteException {}
    @Override public java.util.List<android.media.AudioDeviceAttributes> getSpatializerCompatibleAudioDevices() throws android.os.RemoteException { return null; }
    @Override public void addSpatializerCompatibleAudioDevice(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException {}
    @Override public void removeSpatializerCompatibleAudioDevice(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException {}
    @Override public void setDesiredHeadTrackingMode(int p0) throws android.os.RemoteException {}
    @Override public int getDesiredHeadTrackingMode() throws android.os.RemoteException { return 0; }
    @Override public int[] getSupportedHeadTrackingModes() throws android.os.RemoteException { return null; }
    @Override public int getActualHeadTrackingMode() throws android.os.RemoteException { return 0; }
    @Override public void setSpatializerGlobalTransform(float[] p0) throws android.os.RemoteException {}
    @Override public void recenterHeadTracker() throws android.os.RemoteException {}
    @Override public void setSpatializerParameter(int p0, byte[] p1) throws android.os.RemoteException {}
    @Override public void getSpatializerParameter(int p0, byte[] p1) throws android.os.RemoteException {}
    @Override public int getSpatializerOutput() throws android.os.RemoteException { return 0; }
    @Override public void registerSpatializerOutputCallback(android.media.ISpatializerOutputCallback p0) throws android.os.RemoteException {}
    @Override public void unregisterSpatializerOutputCallback(android.media.ISpatializerOutputCallback p0) throws android.os.RemoteException {}
    @Override public boolean isVolumeFixed() throws android.os.RemoteException { return false; }
    @Override public android.media.VolumeInfo getDefaultVolumeInfo() throws android.os.RemoteException { return null; }
    @Override public boolean isPstnCallAudioInterceptable() throws android.os.RemoteException { return false; }
    @Override public void muteAwaitConnection(int[] p0, android.media.AudioDeviceAttributes p1, long p2) throws android.os.RemoteException {}
    @Override public void cancelMuteAwaitConnection(android.media.AudioDeviceAttributes p0) throws android.os.RemoteException {}
    @Override public android.media.AudioDeviceAttributes getMutingExpectedDevice() throws android.os.RemoteException { return null; }
    @Override public void registerMuteAwaitConnectionDispatcher(android.media.IMuteAwaitConnectionCallback p0, boolean p1) throws android.os.RemoteException {}
    @Override public void setTestDeviceConnectionState(android.media.AudioDeviceAttributes p0, boolean p1) throws android.os.RemoteException {}
    @Override public void registerDeviceVolumeBehaviorDispatcher(boolean p0, android.media.IDeviceVolumeBehaviorDispatcher p1) throws android.os.RemoteException {}
    @Override public java.util.List<android.media.AudioFocusInfo> getFocusStack() throws android.os.RemoteException { return null; }
    @Override public boolean sendFocusLoss(android.media.AudioFocusInfo p0, android.media.audiopolicy.IAudioPolicyCallback p1) throws android.os.RemoteException { return false; }
    @Override public void addAssistantServicesUids(int[] p0) throws android.os.RemoteException {}
    @Override public void removeAssistantServicesUids(int[] p0) throws android.os.RemoteException {}
    @Override public void setActiveAssistantServiceUids(int[] p0) throws android.os.RemoteException {}
    @Override public int[] getAssistantServicesUids() throws android.os.RemoteException { return null; }
    @Override public int[] getActiveAssistantServiceUids() throws android.os.RemoteException { return null; }
    @Override public void registerDeviceVolumeDispatcherForAbsoluteVolume(boolean p0, android.media.IAudioDeviceVolumeDispatcher p1, java.lang.String p2, android.media.AudioDeviceAttributes p3, java.util.List<android.media.VolumeInfo> p4, boolean p5, int p6) throws android.os.RemoteException {}
    @Override public android.media.AudioHalVersionInfo getHalVersion() throws android.os.RemoteException { return null; }
    @Override public int setPreferredMixerAttributes(android.media.AudioAttributes p0, int p1, android.media.AudioMixerAttributes p2) throws android.os.RemoteException { return 0; }
    @Override public int clearPreferredMixerAttributes(android.media.AudioAttributes p0, int p1) throws android.os.RemoteException { return 0; }
    @Override public void registerPreferredMixerAttributesDispatcher(android.media.IPreferredMixerAttributesDispatcher p0) throws android.os.RemoteException {}
    @Override public void unregisterPreferredMixerAttributesDispatcher(android.media.IPreferredMixerAttributesDispatcher p0) throws android.os.RemoteException {}
    @Override public boolean supportsBluetoothVariableLatency() throws android.os.RemoteException { return false; }
    @Override public void setBluetoothVariableLatencyEnabled(boolean p0) throws android.os.RemoteException {}
    @Override public boolean isBluetoothVariableLatencyEnabled() throws android.os.RemoteException { return false; }
}
