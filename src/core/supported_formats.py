"""Central definition of supported media formats"""

SUPPORTED_FORMATS = {
    'photo': {
        'common': {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'},
        'raw': {'.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2', '.raf',
                '.raw', '.rwl', '.dcr', '.srw', '.x3f'},
        'modern': {'.heic', '.heif', '.webp', '.avif', '.jxl'},
        'professional': {'.psd', '.exr', '.hdr', '.tga'},
        'other': {'.svg', '.pbm', '.pgm', '.ppm'}
    },
    'video': {
        'common': {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
                   '.m4v', '.mpg', '.mpeg'},
        'professional': {'.mxf', '.r3d', '.braw', '.ari', '.prores'},
        'mobile': {'.3gp', '.3g2', '.mts', '.m2ts'},
        'other': {'.ts', '.vob', '.ogv', '.rm', '.rmvb', '.asf', '.m2v',
                  '.f4v', '.mod', '.tod'}
    }
}

# Combine all formats into a single set
ALL_SUPPORTED_EXTENSIONS = set()
for category in SUPPORTED_FORMATS.values():
    for format_set in category.values():
        ALL_SUPPORTED_EXTENSIONS.update(format_set)


# Helper functions
def is_supported_format(filename):
    """Check if a filename has a supported extension"""
    import os
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALL_SUPPORTED_EXTENSIONS


def get_format_category(filename):
    """Get the category (photo/video) for a filename"""
    import os
    ext = os.path.splitext(filename)[1].lower()

    for category, formats in SUPPORTED_FORMATS.items():
        for format_set in formats.values():
            if ext in format_set:
                return category
    return None