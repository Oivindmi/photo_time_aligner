class PhotoTimeAlignerError(Exception):
    """Base exception for Photo Time Aligner"""
    pass

class ExifToolNotFoundError(PhotoTimeAlignerError):
    """Raised when ExifTool executable cannot be found"""
    pass

class ExifToolError(PhotoTimeAlignerError):
    """Raised when ExifTool encounters an error"""
    pass

class FileProcessingError(PhotoTimeAlignerError):
    """Raised when file processing fails"""
    pass