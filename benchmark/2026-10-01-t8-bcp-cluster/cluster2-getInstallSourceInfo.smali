# T8 item ② surgical patch — adapter.packagemanager.PackageManagerAdapter.getInstallSourceInfo
# oh-adapter-framework.jar (BCP, deployed j10g-238ffc14). baksmali -> replace this ONE method body ->
# smali 2.5.2 -a 29 -> dex 039 (CLAMP48 path). 0 deletions elsewhere. Return an all-null InstallSourceInfo
# ("installed by nobody") instead of null, so PackageManager.getInstallSourceInfo(self) stops throwing
# NameNotFound (cv2-org-secuso-privacyfriendlyyahtzeedicer).
#
# InstallSourceInfo ctor used (PUBLIC 0x10001 in the deployed framework.jar):
#   (Ljava/lang/String;Landroid/content/pm/SigningInfo;Ljava/lang/String;Ljava/lang/String;)V
#   = (initiatingPackageName, initiatingPackageSigningInfo, originatingPackageName, installingPackageName)

.method public getInstallSourceInfo(Ljava/lang/String;I)Landroid/content/pm/InstallSourceInfo;
    .locals 5
    const-string v0, "getInstallSourceInfo"
    const-string v1, ""
    invoke-direct {p0, v0, v1}, Ladapter/packagemanager/PackageManagerAdapter;->logStub(Ljava/lang/String;Ljava/lang/String;)V
    new-instance v0, Landroid/content/pm/InstallSourceInfo;
    const/4 v1, 0x0
    const/4 v2, 0x0
    const/4 v3, 0x0
    const/4 v4, 0x0
    invoke-direct {v0, v1, v2, v3, v4}, Landroid/content/pm/InstallSourceInfo;-><init>(Ljava/lang/String;Landroid/content/pm/SigningInfo;Ljava/lang/String;Ljava/lang/String;)V
    return-object v0
.end method
