"""FileEngine BCF-API subservice (Phase F / §12 of the xeokit upgrade/BCF plan).

The BCF (BIM Collaboration Format) protocol door: a FastAPI adapter that lets
external AEC tools (Revit/Navisworks/Solibri/BIMcollab) collaborate live against
FileEngine over BCF-API 2.1. It is *not* a second issue store — topics and
comments live in the discussion substrate (reached through the shared
``comment_store`` interface); this service owns only the BCF projection tables.
"""

__version__ = "0.1.0"
