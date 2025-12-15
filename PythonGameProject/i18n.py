import json
import os


class TranslationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance.translations = {}
            cls._instance.locale = "ko"  # 기본 로케일
            cls._instance.load_translations()
        return cls._instance

    def load_translations(self):
        locale_dir = os.path.join(os.path.dirname(__file__), "data", "locales")
        if not os.path.exists(locale_dir):
            os.makedirs(locale_dir)
            return

        for filename in os.listdir(locale_dir):
            if filename.endswith(".json"):
                lang = filename.split(".")[0]
                try:
                    with open(
                        os.path.join(locale_dir, filename), "r", encoding="utf-8"
                    ) as f:
                        self.translations[lang] = json.load(f)
                except Exception as e:
                    print(f"Failed to load translation for {lang}: {e}")

    def set_locale(self, locale):
        if locale in self.translations:
            self.locale = locale
        else:
            print(f"Locale {locale} not found.")

    def get(self, key, default=None, **kwargs):
        keys = key.split(".")
        value = self.translations.get(self.locale, {})

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return (
                    default if default is not None else key
                )  # Return default or key if not found

        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        return value


# Global instance
i18n = TranslationManager()
