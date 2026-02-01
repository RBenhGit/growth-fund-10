"""
מקור נתונים - חריגים מותאמים אישית
Data Source Custom Exceptions for clear error handling
"""


class DataSourceError(Exception):
    """
    בסיס לכל שגיאות מקור נתונים
    Base class for all data source errors
    """
    pass


class DataSourceConnectionError(DataSourceError):
    """
    שגיאת התחברות למקור נתונים
    Connection error to data source (network issues, timeout, etc.)
    """
    pass


class DataSourceAuthenticationError(DataSourceError):
    """
    שגיאת אימות (API key שגוי או לא תקף)
    Authentication error (invalid or expired API key)
    """
    pass


class DataSourceRateLimitError(DataSourceError):
    """
    חריגה ממכסת קריאות API
    API rate limit exceeded
    """
    pass


class DataSourceNotFoundError(DataSourceError):
    """
    מניה או מדד לא נמצא במקור הנתונים
    Stock or index not found in data source
    """
    pass


class DataSourceNotSupportedError(DataSourceError):
    """
    מקור הנתונים לא תומך במדד או במניה זו
    Data source doesn't support this index or stock
    """
    pass


class DataSourceDataQualityError(DataSourceError):
    """
    נתונים חסרים, לא תקינים, או באיכות נמוכה
    Missing, invalid, or low-quality data
    """
    pass


class DataSourceConfigurationError(DataSourceError):
    """
    שגיאה בהגדרות מקור הנתונים
    Configuration error for data source
    """
    pass
