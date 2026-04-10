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
  // Flashcard flow
  Flashcards: undefined;
  FlashcardTopics: { specialty: string };
  FlashcardDecks: { specialty: string; topic: string };
  FlashcardViewer: { specialty: string; topic: string; deckName: string };
  // Simulacros flow
  Simulacros: undefined;
  SimulacroExam: { simulacroId: string; viewResults: boolean };
  Duels: undefined;
  DuelGame: { duelId: string; opponentName: string; opponentImage?: string };
  ImagenDX: undefined;
  Planner: undefined;
  Perlas: undefined;
  Presentaciones: undefined;
  Leaderboard: undefined;
  CaminoDelMedico: undefined;
  Journal: undefined;
  Support: undefined;
};
