from .simple_transform import SimpleTransform
from .simple_transform_3d_smpl import SimpleTransform3DSMPL
from .simple_transform_3d_smpl_cam import SimpleTransform3DSMPLCam
from .simple_transform_cam import SimpleTransformCam

# SMPLX requires pytorch3d - make it optional
try:
    from .simple_transform_3d_smplx import SimpleTransform3DSMPLX
    SMPLX_TRANSFORM_AVAILABLE = True
except ImportError:
    SimpleTransform3DSMPLX = None
    SMPLX_TRANSFORM_AVAILABLE = False

__all__ = [
    'SimpleTransform', 'SimpleTransform3DSMPL', 'SimpleTransform3DSMPLCam', 'SimpleTransformCam',
    'SimpleTransform3DSMPLX', 'SMPLX_TRANSFORM_AVAILABLE']
