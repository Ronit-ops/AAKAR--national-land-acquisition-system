import type { ChangeEvent } from 'react';
import { useAakarLanguage } from '../i18n/i18n';

export default function LanguageSelector() {
  const { language, languages, t, setLanguage } = useAakarLanguage();

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setLanguage(event.target.value as typeof language);
  };

  return (
    <div className="aakar-language-control">
      <div className="aakar-language-control-icon" aria-hidden="true">
        <span>文</span>
      </div>

      <div className="aakar-language-control-content">
        <span className="aakar-language-control-label">
          {t('common.language')}
        </span>

        <select
          className="aakar-language-control-select"
          value={language}
          onChange={handleChange}
          aria-label={t('common.language')}
        >
          {languages.map((item) => (
            <option key={item.code} value={item.code}>
              {item.nativeName} — {item.name}
            </option>
          ))}
        </select>
      </div>

      <span className="aakar-language-control-chevron" aria-hidden="true">
        ▾
      </span>
    </div>
  );
}