export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  Home: undefined;
  Profile: undefined;
  // Quiz flow
  Cuestionarios: undefined;
  Submodules: { specialty: string };
  Topics: { specialty: string; submodule?: string };
  Quiz: { quizId: string };
  // Other features (Phase 3+)
  Flashcards: undefined;
  Simulacros: undefined;
  Duels: undefined;
  ImagenDX: undefined;
  Planner: undefined;
  Perlas: undefined;
  Presentaciones: undefined;
  Leaderboard: undefined;
  CaminoDelMedico: undefined;
  Journal: undefined;
  Support: undefined;
};
