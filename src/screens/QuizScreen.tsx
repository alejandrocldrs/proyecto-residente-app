import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Alert, Modal,
} from 'react-native';
import { RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Quiz'>;
  route: RouteProp<RootStackParamList, 'Quiz'>;
};

interface Question {
  id: string;
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_answer: string; // 'A' | 'B' | 'C' | 'D'
  explanation?: string;
  reference?: string;
}

interface QuizData {
  id: string;
  topic: string;
  title?: string;
  specialty: string;
}

interface Results {
  score: number;
  correct_answers: number;
  total_questions: number;
}

const OPTIONS = ['A', 'B', 'C', 'D'] as const;

export default function QuizScreen({ navigation, route }: Props) {
  const { quizId } = route.params;

  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [showFeedback, setShowFeedback] = useState<Record<string, boolean>>({});
  const [savedFlashcards, setSavedFlashcards] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState<Results | null>(null);
  const [showAbandonModal, setShowAbandonModal] = useState(false);

  useEffect(() => {
    fetchQuiz();
  }, [quizId]);

  useEffect(() => {
    if (quiz) loadProgress();
  }, [quiz]);

  useEffect(() => {
    if (quiz && Object.keys(answers).length > 0) saveProgress();
  }, [answers, currentIndex]);

  // Check flashcard status when feedback is shown for current question
  useEffect(() => {
    const q = questions[currentIndex];
    if (q && showFeedback[q.id]) checkFlashcard(q.id);
  }, [showFeedback, currentIndex, questions]);

  const fetchQuiz = async () => {
    try {
      const res = await api.get(`/api/quizzes/${quizId}`);
      setQuiz(res.data.quiz);
      setQuestions(res.data.questions);
    } catch {
      Alert.alert('Error', 'No se pudo cargar el cuestionario');
      navigation.goBack();
    } finally {
      setLoading(false);
    }
  };

  const loadProgress = async () => {
    try {
      const res = await api.get(`/api/quiz-progress/${quizId}`);
      if (res.data) {
        setCurrentIndex(res.data.current_question_index ?? 0);
        setAnswers(res.data.answers ?? {});
        const feedback: Record<string, boolean> = {};
        Object.keys(res.data.answers ?? {}).forEach((id) => { feedback[id] = true; });
        setShowFeedback(feedback);
      }
    } catch {}
  };

  const saveProgress = useCallback(async () => {
    if (!quiz) return;
    try {
      await api.post('/api/quiz-progress', {
        quiz_id: quizId,
        current_question_index: currentIndex,
        answers,
      });
    } catch {}
  }, [quiz, quizId, currentIndex, answers]);

  const checkFlashcard = async (questionId: string) => {
    try {
      const res = await api.get(`/api/flashcards/check/${questionId}`);
      if (res.data.exists) setSavedFlashcards((p) => ({ ...p, [questionId]: true }));
    } catch {}
  };

  const toggleFlashcard = async (q: Question) => {
    const isSaved = savedFlashcards[q.id];
    try {
      if (isSaved) {
        await api.delete(`/api/flashcards/by-question/${q.id}`);
        setSavedFlashcards((p) => { const n = { ...p }; delete n[q.id]; return n; });
      } else {
        const correctKey = `option_${q.correct_answer.toLowerCase()}` as keyof Question;
        await api.post('/api/flashcards', {
          question_id: q.id,
          quiz_id: quizId,
          quiz_title: quiz?.topic,
          specialty: quiz?.specialty,
          topic: quiz?.topic,
          question_text: q.question_text,
          answer_text: q[correctKey],
          explanation: q.explanation ?? null,
        });
        setSavedFlashcards((p) => ({ ...p, [q.id]: true }));
      }
    } catch {}
  };

  const handleAnswer = (questionId: string, option: string) => {
    if (showFeedback[questionId]) return;
    setAnswers((p) => ({ ...p, [questionId]: option }));
    setShowFeedback((p) => ({ ...p, [questionId]: true }));
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1);
    }
  };

  const submitQuiz = async () => {
    const unanswered = questions.filter((q) => !answers[q.id]);
    if (unanswered.length > 0) {
      Alert.alert('Faltan preguntas', `Tienes ${unanswered.length} pregunta(s) sin responder.`);
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/api/quiz-attempts', { quiz_id: quizId, answers });
      setResults(res.data);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'Error al enviar respuestas');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAbandon = async () => {
    await saveProgress();
    setShowAbandonModal(false);
    navigation.goBack();
  };

  const retryQuiz = () => {
    setCurrentIndex(0);
    setAnswers({});
    setShowFeedback({});
    setSavedFlashcards({});
    setResults(null);
  };

  // ─── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#6366F1" />
      </View>
    );
  }

  // ─── Results ───────────────────────────────────────────────────────────────
  if (results) {
    const { score, correct_answers, total_questions } = results;
    const scoreColor = score >= 90 ? '#22C55E' : score >= 70 ? '#F59E0B' : '#EF4444';
    const message = score >= 90 ? '¡Excelente dominio del tema!' : score >= 70 ? 'Buen trabajo, sigue practicando.' : 'Necesitas repasar este tema.';

    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.resultsContent}>
          <Text style={styles.resultsEmoji}>🏆</Text>
          <Text style={styles.resultsTitle}>¡Cuestionario Completado!</Text>
          <Text style={styles.resultsSubtitle}>{quiz?.topic}</Text>

          <View style={[styles.scoreCard, { borderColor: scoreColor }]}>
            <Text style={[styles.scorePercent, { color: scoreColor }]}>
              {score.toFixed(1)}%
            </Text>
            <Text style={styles.scoreDetail}>
              {correct_answers} de {total_questions} correctas
            </Text>
            <Text style={styles.scoreMessage}>{message}</Text>
          </View>

          <TouchableOpacity style={styles.btnPrimary} onPress={retryQuiz}>
            <Text style={styles.btnPrimaryText}>🔄 Volver a Intentar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.btnSecondary} onPress={() => navigation.navigate('Cuestionarios')}>
            <Text style={styles.btnSecondaryText}>Volver a Cuestionarios</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ─── Quiz ──────────────────────────────────────────────────────────────────
  const q = questions[currentIndex];
  if (!q) return null;

  const progress = ((currentIndex + 1) / questions.length) * 100;
  const isLast = currentIndex === questions.length - 1;
  const answered = !!answers[q.id];
  const feedbackVisible = !!showFeedback[q.id];

  return (
    <SafeAreaView style={styles.container}>
      {/* Progress bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>{currentIndex + 1}/{questions.length}</Text>
      </View>

      <ScrollView contentContainerStyle={styles.quizContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.questionTitle}>{quiz?.topic}</Text>
        <Text style={styles.questionText}>{q.question_text}</Text>

        {/* Options */}
        <View style={styles.optionsContainer}>
          {OPTIONS.map((opt) => {
            const key = `option_${opt.toLowerCase()}` as keyof Question;
            const text = q[key] as string;
            if (!text || text === 'undefined' || text === 'null' || !text.trim()) return null;

            const isSelected = answers[q.id] === opt;
            const isCorrect = q.correct_answer === opt;

            let optStyle = styles.option;
            let textStyle = styles.optionText;
            let labelStyle = styles.optionLabel;

            if (feedbackVisible) {
              if (isCorrect) { optStyle = { ...styles.option, ...styles.optionCorrect }; textStyle = { ...styles.optionText, ...styles.optionTextCorrect }; labelStyle = { ...styles.optionLabel, ...styles.optionTextCorrect }; }
              else if (isSelected) { optStyle = { ...styles.option, ...styles.optionWrong }; textStyle = { ...styles.optionText, ...styles.optionTextWrong }; labelStyle = { ...styles.optionLabel, ...styles.optionTextWrong }; }
            } else if (isSelected) {
              optStyle = { ...styles.option, ...styles.optionSelected };
            }

            return (
              <TouchableOpacity
                key={opt}
                style={optStyle}
                onPress={() => handleAnswer(q.id, opt)}
                activeOpacity={feedbackVisible ? 1 : 0.7}
              >
                <Text style={labelStyle}>{opt}.</Text>
                <Text style={textStyle}>{text}</Text>
                {feedbackVisible && isCorrect && <Text style={styles.optionIcon}>✓</Text>}
                {feedbackVisible && isSelected && !isCorrect && <Text style={styles.optionIcon}>✗</Text>}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Placeholder when no answer */}
        {!answered && (
          <Text style={styles.selectHint}>Selecciona una respuesta para continuar</Text>
        )}

        {/* Feedback */}
        {feedbackVisible && (
          <View style={styles.feedbackBox}>
            <Text style={[styles.feedbackResult, answers[q.id] === q.correct_answer ? styles.correct : styles.wrong]}>
              {answers[q.id] === q.correct_answer ? '✓ ¡Correcto!' : '✗ Incorrecto'}
            </Text>
            <Text style={styles.feedbackCorrect}>
              Respuesta correcta: <Text style={styles.bold}>{q.correct_answer}</Text>
            </Text>
            {!!q.explanation?.trim() && q.explanation !== 'undefined' && (
              <Text style={styles.feedbackExplanation}>
                <Text style={styles.bold}>Explicación: </Text>{q.explanation}
              </Text>
            )}
            {!!q.reference?.trim() && q.reference !== 'undefined' && (
              <Text style={styles.feedbackExplanation}>
                <Text style={styles.bold}>Referencia: </Text>{q.reference}
              </Text>
            )}

            {/* Flashcard toggle */}
            <TouchableOpacity
              style={[styles.flashcardBtn, savedFlashcards[q.id] && styles.flashcardBtnSaved]}
              onPress={() => toggleFlashcard(q)}
            >
              <Text style={[styles.flashcardBtnText, savedFlashcards[q.id] && styles.flashcardBtnTextSaved]}>
                {savedFlashcards[q.id] ? '🔖 Guardada en Flashcards ✓' : '🔖 Agregar a Flashcards'}
              </Text>
            </TouchableOpacity>

            {/* Next / Finish */}
            {!isLast ? (
              <TouchableOpacity style={styles.btnPrimary} onPress={handleNext}>
                <Text style={styles.btnPrimaryText}>Siguiente →</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={styles.btnPrimary}
                onPress={submitQuiz}
                disabled={submitting}
              >
                {submitting
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.btnPrimaryText}>Finalizar Cuestionario</Text>}
              </TouchableOpacity>
            )}
          </View>
        )}
      </ScrollView>

      {/* Abandon button */}
      <TouchableOpacity style={styles.abandonBtn} onPress={() => setShowAbandonModal(true)}>
        <Text style={styles.abandonText}>Abandonar</Text>
      </TouchableOpacity>

      {/* Abandon modal */}
      <Modal transparent visible={showAbandonModal} animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>¿Abandonar cuestionario?</Text>
            <Text style={styles.modalBody}>
              Tu progreso se guardará y podrás continuar desde donde te quedaste.
            </Text>
            <TouchableOpacity style={styles.btnDanger} onPress={handleAbandon}>
              <Text style={styles.btnPrimaryText}>Sí, abandonar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnSecondary} onPress={() => setShowAbandonModal(false)}>
              <Text style={styles.btnSecondaryText}>Continuar estudiando</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },

  // Progress
  progressContainer: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 10, gap: 10 },
  progressTrack: { flex: 1, height: 4, backgroundColor: '#1E293B', borderRadius: 2, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#6366F1', borderRadius: 2 },
  progressText: { color: '#64748B', fontSize: 12, width: 40, textAlign: 'right' },

  // Quiz
  quizContent: { padding: 20, paddingBottom: 80 },
  questionTitle: { fontSize: 13, color: '#6366F1', fontWeight: '600', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 },
  questionText: { fontSize: 17, color: '#F8FAFC', fontWeight: '500', lineHeight: 26, marginBottom: 24 },

  optionsContainer: { gap: 10, marginBottom: 8 },
  option: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#1E293B', borderRadius: 12, padding: 14, borderWidth: 1.5, borderColor: '#334155', gap: 10 },
  optionSelected: { borderColor: '#6366F1', backgroundColor: '#1E1B4B' },
  optionCorrect: { borderColor: '#22C55E', backgroundColor: '#052E16' },
  optionWrong: { borderColor: '#EF4444', backgroundColor: '#2D0A0A' },
  optionLabel: { fontSize: 15, fontWeight: '700', color: '#94A3B8', width: 22 },
  optionText: { flex: 1, fontSize: 14, color: '#CBD5E1', lineHeight: 21 },
  optionTextCorrect: { color: '#22C55E' },
  optionTextWrong: { color: '#EF4444' },
  optionIcon: { fontSize: 18, marginLeft: 4 },

  selectHint: { textAlign: 'center', color: '#475569', fontSize: 13, marginTop: 8 },

  // Feedback
  feedbackBox: { backgroundColor: '#1E293B', borderRadius: 16, padding: 18, marginTop: 16, borderWidth: 1, borderColor: '#334155', gap: 10 },
  feedbackResult: { fontSize: 16, fontWeight: '700' },
  correct: { color: '#22C55E' },
  wrong: { color: '#EF4444' },
  feedbackCorrect: { fontSize: 14, color: '#94A3B8' },
  feedbackExplanation: { fontSize: 13, color: '#94A3B8', lineHeight: 20 },
  bold: { fontWeight: '700', color: '#CBD5E1' },

  flashcardBtn: { backgroundColor: '#0F172A', borderRadius: 10, padding: 12, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  flashcardBtnSaved: { backgroundColor: '#1E3A2F', borderColor: '#22C55E' },
  flashcardBtnText: { color: '#94A3B8', fontSize: 13 },
  flashcardBtnTextSaved: { color: '#22C55E' },

  // Buttons
  btnPrimary: { backgroundColor: '#6366F1', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  btnPrimaryText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnSecondary: { backgroundColor: '#1E293B', borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  btnSecondaryText: { color: '#94A3B8', fontSize: 15 },
  btnDanger: { backgroundColor: '#DC2626', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },

  abandonBtn: { position: 'absolute', bottom: 16, right: 20 },
  abandonText: { color: '#EF4444', fontSize: 13 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 32 },
  modalBox: { backgroundColor: '#1E293B', borderRadius: 20, padding: 24, width: '100%', gap: 12, borderWidth: 1, borderColor: '#334155' },
  modalTitle: { fontSize: 18, fontWeight: 'bold', color: '#F8FAFC' },
  modalBody: { fontSize: 14, color: '#94A3B8', lineHeight: 21 },

  // Results
  resultsContent: { padding: 32, alignItems: 'center', gap: 16 },
  resultsEmoji: { fontSize: 64 },
  resultsTitle: { fontSize: 24, fontWeight: 'bold', color: '#F8FAFC' },
  resultsSubtitle: { fontSize: 14, color: '#64748B', textAlign: 'center' },
  scoreCard: { width: '100%', backgroundColor: '#1E293B', borderRadius: 20, padding: 28, alignItems: 'center', borderWidth: 2, gap: 8 },
  scorePercent: { fontSize: 52, fontWeight: 'bold' },
  scoreDetail: { fontSize: 16, color: '#94A3B8' },
  scoreMessage: { fontSize: 14, color: '#64748B', textAlign: 'center' },
});
