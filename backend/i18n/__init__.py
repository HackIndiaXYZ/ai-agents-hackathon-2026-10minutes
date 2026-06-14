"""
i18n/ — On-demand UI translation.

The frontend defines all interface strings in English (the source of truth) and
requests translations for the active language. This package translates string
batches via Gemini and caches each translation in Redis so the same string is
never re-translated. Nothing is hardcoded per language — translations are
generated on first use and cached.
"""
