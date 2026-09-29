/** The languages Pankh writes to students and schools in (backend/app/languages.py). */
export const LANGUAGES = [
  { value: "hi", label: "हिन्दी", english: "Hindi" },
  { value: "en", label: "English", english: "English" },
  { value: "bn", label: "বাংলা", english: "Bengali" },
  { value: "gu", label: "ગુજરાતી", english: "Gujarati" },
  { value: "mr", label: "मराठी", english: "Marathi" },
  { value: "or", label: "ଓଡ଼ିଆ", english: "Odia" },
] as const;

export type Language = (typeof LANGUAGES)[number]["value"];

export function languageName(language: Language): string {
  return LANGUAGES.find((option) => option.value === language)?.english ?? language;
}
