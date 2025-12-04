from .simple3dposeBaseSMPL import Simple3DPoseBaseSMPL
from .simple3dposeBaseSMPL24 import Simple3DPoseBaseSMPL24
from .simple3dposeSMPLWithCam import Simple3DPoseBaseSMPLCam
from .simple3dposeSMPLWithCamReg import Simple3DPoseBaseSMPLCamReg
from .HRNetWithCam import HRNetSMPLCam
from .HRNetWithCamReg import HRNetSMPLCamReg
from .criterion import *  # noqa: F401,F403

# SMPLX models require pytorch3d - make them optional
try:
    from .HRNetSMPLXCamKid import HRNetSMPLXCamKid
    from .HRNetSMPLXCamKidReg import HRNetSMPLXCamKidReg
    SMPLX_AVAILABLE = True
except ImportError:
    HRNetSMPLXCamKid = None
    HRNetSMPLXCamKidReg = None
    SMPLX_AVAILABLE = False

__all__ = [
    'Simple3DPoseBaseSMPL', 'Simple3DPoseBaseSMPL24', 'Simple3DPoseBaseSMPLCam',
    'Simple3DPoseBaseSMPLCamReg',
    'HRNetSMPLCam', 'HRNetSMPLCamReg',
    'HRNetSMPLXCamKid', 'HRNetSMPLXCamKidReg',
    'SMPLX_AVAILABLE']
