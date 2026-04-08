export const specialtyStructure: Record<string, { hasSubmodules: boolean; submodules: string[] }> = {
  "Medicina Interna": {
    hasSubmodules: true,
    submodules: ["Cardiología","Dermatología","Endocrinología","Gastroenterología","Hematología","Infectología","Medicina Interna (general)","Nefrología","Neumología","Neurología","Oncología","Reumatología"]
  },
  "Cirugía": {
    hasSubmodules: true,
    submodules: ["Angiología","Cirugía General","Cirugía Maxilofacial","Cirugía Plástica","Neurocirugía","Oftalmología","Otorrinolaringología","Trasplantes","Traumatología y Ortopedia","Urología"]
  },
  "Ginecología y Obstetricia": { hasSubmodules: false, submodules: [] },
  "Pediatría": { hasSubmodules: false, submodules: [] },
  "Otros": {
    hasSubmodules: true,
    submodules: ["Alergia e Inmunología","Analgesia y Anestesia","Enfermedades Lisosomales","Genética","Geriatría","Medicina Familiar","Medicina Física y Rehabilitación","Nutriología","Psiquiatría","Urgencias Médico-Quirúrgicas"]
  }
};

export const baseSpecialties = [
  "Medicina Interna",
  "Cirugía",
  "Ginecología y Obstetricia",
  "Pediatría",
  "Otros"
];

export const getSubmodules = (specialty: string): string[] =>
  specialtyStructure[specialty]?.submodules ?? [];

export const hasSubmodules = (specialty: string): boolean =>
  specialtyStructure[specialty]?.hasSubmodules ?? false;

export const specialtyEmoji: Record<string, string> = {
  "Medicina Interna": "🫀",
  "Cirugía": "🔪",
  "Ginecología y Obstetricia": "🤰",
  "Pediatría": "👶",
  "Otros": "🩺",
};
