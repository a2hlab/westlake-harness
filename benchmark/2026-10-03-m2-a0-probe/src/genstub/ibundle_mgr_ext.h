// Stand-in for the IDL-generated header (IBundleMgrExt.idl; the hw248 source tree has no generated out/ for it).
// bundle_mgr_interface.h only uses the type as sptr<IBundleMgrExt> (inline defaults return nullptr), which needs a
// complete RefBase-derived type. This empty class is never instantiated; the probe never calls into bundle manager
// interfaces, and the probe is built -fvisibility=hidden, so the stand-in does not leave this .so.
#ifndef WL_A0_GENSTUB_IBUNDLE_MGR_EXT_H
#define WL_A0_GENSTUB_IBUNDLE_MGR_EXT_H
#include "refbase.h"
namespace OHOS {
namespace AppExecFwk {
class IBundleMgrExt : public virtual OHOS::RefBase {};
} // namespace AppExecFwk
} // namespace OHOS
#endif
