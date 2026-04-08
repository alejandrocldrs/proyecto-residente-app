# Proyecto Residente — Mobile App Rewrite Log

## Overview

**Goal:** Rewrite the Proyecto Residente web app as a native mobile app (Expo/React Native) publishable to the App Store and Google Play.

**Original app:** React PWA built with Emergent, hosted at [proyectoresidente.com](https://proyectoresidente.com)  
**Original source:** VS Code server at Emergent (password-protected)  
**Backend:** Python/Flask, live at `https://landing-residente.emergent.host`  
**New repo:** [github.com/alejandrocldrs/proyecto-residente-app](https://github.com/alejandrocldrs/proyecto-residente-app)  
**Approach:** Phase by phase — core features first, UX/UI polish at the end

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Expo SDK 54 (managed workflow) |
| Language | TypeScript |
| Navigation | React Navigation v6 (native stack) |
| State / Auth | Zustand + expo-secure-store |
| HTTP client | axios |
| Theme | Dark (`#0F172A` base) |
| Payments | MercadoPago (Phase 5) |

---

## App Features (from original web app)

| Feature | Screen(s) | Phase | Status |
|---|---|---|---|
| Login / Register | LoginScreen, RegisterScreen | 1 | ✅ Done |
| Home hub | HomeScreen | 1 | ✅ Done |
| Specialty selection | CuestionariosScreen | 2 | ✅ Done |
| Submodule selection | SubmodulesScreen | 2 | ✅ Done |
| Topic list | TopicsScreen | 2 | ✅ Done |
| Quiz with feedback | QuizScreen | 2 | ✅ Done |
| Flashcards | FlashcardsScreen, FlashcardViewerScreen | 3 | 🔲 Pending |
| Mock exams (simulacros) | SimulacrosScreen, SimulacroExamScreen | 3 | 🔲 Pending |
| Duels | DuelsScreen, DuelGameScreen | 3 | 🔲 Pending |
| Leaderboard | LeaderboardScreen | 3 | 🔲 Pending |
| Daily journal | JournalScreen | 3 | 🔲 Pending |
| Radiology diagnosis | ImagenDXScreen flow | 4 | 🔲 Pending |
| Study planner | StudyPlannerScreen | 4 | 🔲 Pending |
| Presentations | PresentacionesScreen | 4 | 🔲 Pending |
| Daily pearls | PerlasDiariasScreen | 4 | 🔲 Pending |
| ENARM Match | ENARMMatchScreen | 4 | 🔲 Pending |
| Camino del Médico | CaminoDelMedicoScreen | 5 | 🔲 Pending |
| Escape Room | EscapeRoomScreen | 5 | 🔲 Pending |
| Spin Wheel | SpinWheelScreen | 5 | 🔲 Pending |
| Payments (MercadoPago) | PaymentScreen | 5 | 🔲 Pending |
| Support | SupportScreen | 5 | 🔲 Pending |
| Admin panel | AdminScreen | 5 | 🔲 Pending |
| Profile edit | ProfileScreen | 5 | 🔲 Pending |
| UX / UI polish | All screens | 6 | 🔲 Pending |

---

## Backend API — Known Endpoints

### Auth
| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/auth/register` | Body: `{full_name, email, password, gender}` — returns `{message, user_id}` |
| POST | `/api/auth/login` | Body: `{email, password}` — returns `{access_token, token_type}` |
| GET | `/api/auth/me` | Bearer token required — returns full user profile |

### Quizzes
| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/quizzes?specialty={name}` | Returns quiz list for a specialty |
| GET | `/api/quizzes/{quizId}` | Returns `{quiz, questions}` |
| POST | `/api/quiz-attempts` | Body: `{quiz_id, answers}` — returns `{score, correct_answers, total_questions}` |
| GET | `/api/quiz-progress/{quizId}` | Resume saved progress |
| POST | `/api/quiz-progress` | Body: `{quiz_id, current_question_index, answers}` |
| GET | `/api/progress/quizzes` | Returns `{passed: [quizId, ...]}` |
| GET | `/api/progress/pass-counts` | Returns `{pass_counts: {quizId: count}}` |

### Flashcards
| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/flashcards/check/{questionId}` | Returns `{exists: bool}` |
| POST | `/api/flashcards` | Save a flashcard from a quiz question |
| DELETE | `/api/flashcards/by-question/{questionId}` | Remove saved flashcard |

### Other (to be confirmed as we build)
- `/api/simulacros/...`
- `/api/duels/...`
- `/api/leaderboard/...`
- `/api/journal/...`
- `/api/imagendx/...`
- `/api/planner/...`
- `/api/presentations/...`
- `/api/perlas/...`
- `/api/enarm-match/...`
- `/api/support/...`
- MercadoPago via `/api/mercadopago/...`

---

## Data Structures

### User (from `/api/auth/me`)
```ts
{
  id: string
  full_name: string
  email: string
  gender: string           // 'male' | 'female'
  is_admin: boolean
  is_approved: boolean
  profile_image: string | null
  universidad: string | null
  subscription_expires: string | null
  account_type: string     // 'trial' | 'premium' | 'free'
}
```

### Question
```ts
{
  id: string
  question_text: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_answer: string   // 'A' | 'B' | 'C' | 'D'
  explanation?: string
  reference?: string
}
```

### Specialty Structure
5 base specialties: Medicina Interna, Cirugía, Ginecología y Obstetricia, Pediatría, Otros.  
Medicina Interna, Cirugía, and Otros have submodules. See `src/data/specialtyStructure.ts`.

---

## Learnings & Notes

### Environment setup
- Homebrew must be added to PATH after install: `eval "$(/opt/homebrew/bin/brew shellenv)"`
- Expo env vars must be prefixed with `EXPO_PUBLIC_` to be available in the app bundle
- `.env` is gitignored — never commit real credentials

### Package compatibility
- Always use `npx expo install` (not plain `npm install`) for Expo packages — it pins the correct version for the SDK
- Expo SDK 54 required specific downgrades: `expo-secure-store@~15.0.8`, `react-native-safe-area-context@~5.6.0`, `react-native-screens@~4.16.0`
- `enableScreens()` from `react-native-screens` must be called before the app renders (in App.tsx)

### Auth flow
- Login returns only `access_token` — must call `/api/auth/me` separately for user data
- Register does NOT return a token — must auto-login after registration
- Register requires `full_name` (not `username`)
- Token stored in `expo-secure-store`, loaded on app start by `loadStoredAuth()`

### Error handling
- Always surface real API errors (`err?.response?.data?.detail`) instead of generic messages — makes debugging much faster
- Pydantic validation errors return `detail` as an array of objects with `msg` fields

### Navigation
- Screen name in HomeScreen feature cards must exactly match the registered screen name in the navigator
- Route params must always be typed in `RootStackParamList` — undefined params cause "Cannot read property of undefined" crashes

### Backend
- Backend is live at `https://landing-residente.emergent.host` (Emergent-hosted)
- MongoDB runs locally inside the Emergent container — not externally accessible
- If Emergent goes down or the container sleeps, the backend goes offline — long-term we should migrate to a dedicated host (Railway/Render)
- `CORS_ORIGINS="*"` so no CORS issues from mobile

---

## Pending Items / Decisions

- [ ] **Backend hosting:** The backend runs inside Emergent. If the project grows, migrate to Railway or Render with a cloud MongoDB (Atlas free tier). This is blocking for production.
- [ ] **Push notifications:** Duels use SSE for real-time notifications on web. For mobile, SSE may not work reliably in background — may need to switch to push notifications (Expo Notifications).
- [ ] **ImagenDX images:** Hundreds of images are stored in `/app/frontend/public/imagendx/`. These need to be served from a CDN or the backend for the mobile app to load them.
- [ ] **App icons & splash screen:** Icons exist in `/app/frontend/public/icons/`. Need to configure `app.json` with these before App Store submission.
- [ ] **EAS Build setup:** Need to create an Expo account and configure `eas.json` before building for the stores.
- [ ] **MercadoPago on mobile:** The web app uses MercadoPago's JS SDK. For mobile, use a WebView or the MercadoPago React Native SDK.
- [ ] **UX/UI polish pass:** Deferred to Phase 6. Dark theme is in place; improvements to typography, spacing, animations, and branding (logo, colors) to be done once all features are built.
- [ ] **Git identity:** Commits show auto-detected name/email. Run `git config --global user.name` and `git config --global user.email` to set properly.
