import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Modal, Alert, BackHandler,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'SimulacroExam'>;
  route: RouteProp<RootStackParamList, 'SimulacroExam'>;
};

interface Question {
  index: number;
  case_text?: string;
  case_number?: number;
  question_text: string;
  option_a: string; option_b: string; option_c: string; option_d: string;
}

interface Results {
  score_percentage: number;
  correct_answers: number;
  total_questions: number;
  by_especialidad: Record<string, { correct: number; total: number; percentage: number }>;
  by_tema: Array<{ especialidad: string; tema: string; correct: number; total: number; percentage: number }>;
}

const OPTIONS = ['A', 'B', 'C', 'D'] as const;

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

export default function SimulacroExamScreen({ navigation, route }: Props) {
  const { simulacroId, viewResults: viewResultsMode } = route.params;

  const [simulacro, setSimulacro] = useState<{ title: string; questions: Question[] } | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [marked, setMarked] = useState<number[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(5 * 3600);
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<Results | null>(null);
  const [showConfirmFinish, setShowConfirmFinish] = useState(false);
  const [showGrid, setShowGrid] = useState(false);
  const [expandedEsp, setExpandedEsp] = useState<Record<string, boolean>>({});

  const answersRef = useRef(answers);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const saveRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => { answersRef.current = answers; }, [answers]);

  // Block hardware back button during exam
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (!results) { setShowConfirmFinish(true); return true; }
      return false;
    });
    return () => sub.remove();
  }, [results]);

  useEffect(() => {
    const load = async () => {
      try {
        if (viewResultsMode) {
          const [simRes, resultRes] = await Promise.all([
            api.get(`/api/simulacros/${simulacroId}`),
            api.get(`/api/simulacros/${simulacroId}/latest-result`),
          ]);
          setSimulacro(simRes.data);
          if (resultRes.data?.results) setResults(resultRes.data.results);
          else { Alert.alert('Sin resultados', 'No hay resultados disponibles'); navigation.goBack(); }
        } else {
          const [simRes, attemptRes] = await Promise.all([
            api.get(`/api/simulacros/${simulacroId}`),
            api.post(`/api/simulacros/${simulacroId}/start`),
          ]);
          const simData = simRes.data;
          const attempt = attemptRes.data;

          // Reorder by question_order if provided
          if (attempt.question_order?.length) {
            const byIndex: Record<number, Question> = {};
            for (const q of simData.questions) byIndex[q.index] = q;
            simData.questions = attempt.question_order.map((origIdx: number) => byIndex[origIdx]).filter(Boolean);
          }

          setSimulacro(simData);
          setAnswers(attempt.answers ?? {});
          setMarked(attempt.marked ?? []);

          // Compute remaining time
          let startStr: string = attempt.started_at;
          if (startStr && !startStr.endsWith('Z') && !startStr.includes('+')) startStr += 'Z';
          const elapsed = Math.floor((Date.now() - new Date(startStr).getTime()) / 1000);
          const remaining = Math.max(0, (attempt.time_limit_seconds ?? 18000) - elapsed);
          setTimeRemaining(remaining);
          if (remaining <= 0) handleFinish(attempt.answers ?? {});
        }
      } catch (e) {
        Alert.alert('Error', 'No se pudo cargar el simulacro');
        navigation.goBack();
      } finally {
        setLoading(false);
      }
    };
    load();
    return () => { timerRef.current && clearInterval(timerRef.current); saveRef.current && clearInterval(saveRef.current); };
  }, [simulacroId]);

  // Start timer once loaded
  useEffect(() => {
    if (!simulacro || results || viewResultsMode) return;
    timerRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) { clearInterval(timerRef.current!); handleFinish(answersRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);
    saveRef.current = setInterval(() => {
      api.post(`/api/simulacros/${simulacroId}/save`, { answers: answersRef.current, marked }).catch(() => {});
    }, 30000);
    return () => { timerRef.current && clearInterval(timerRef.current); saveRef.current && clearInterval(saveRef.current); };
  }, [simulacro, results]);

  const handleFinish = useCallback(async (finalAnswers?: Record<string, string>) => {
    timerRef.current && clearInterval(timerRef.current);
    saveRef.current && clearInterval(saveRef.current);
    try {
      const res = await api.post(`/api/simulacros/${simulacroId}/finish`, { answers: finalAnswers ?? answersRef.current });
      setResults(res.data);
      setShowConfirmFinish(false);
    } catch {
      Alert.alert('Error', 'No se pudo finalizar el simulacro');
    }
  }, [simulacroId]);

  const handleAnswer = (option: string) => {
    const q = simulacro!.questions[currentIndex];
    const key = String(q.index);
    setAnswers(prev => {
      const next = { ...prev };
      if (next[key] === option) delete next[key]; else next[key] = option;
      return next;
    });
  };

  const toggleMark = () => {
    setMarked(prev => prev.includes(currentIndex) ? prev.filter(i => i !== currentIndex) : [...prev, currentIndex]);
  };

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#1D4ED8" /></View>;
  }

  // ── Results View ────────────────────────────────────────────────────────────
  if (results) {
    const { score_percentage, correct_answers, total_questions, by_especialidad, by_tema } = results;
    const passed = score_percentage >= 60;
    const scoreColor = score_percentage >= 80 ? '#22C55E' : score_percentage >= 60 ? '#EAB308' : '#EF4444';
    const temasByEsp: Record<string, typeof by_tema> = {};
    for (const t of by_tema) { if (!temasByEsp[t.especialidad]) temasByEsp[t.especialidad] = []; temasByEsp[t.especialidad].push(t); }

    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.resultsContent}>
          <View style={styles.resultsHeader}>
            <Text style={styles.resultsHeaderTitle}>Resultados del Simulacro</Text>
            <Text style={styles.resultsHeaderSub}>{simulacro?.title}</Text>
          </View>

          {/* Score card */}
          <View style={[styles.scoreCard, { borderColor: scoreColor }]}>
            <Text style={[styles.scorePercent, { color: scoreColor }]}>{score_percentage}%</Text>
            <Text style={styles.scoreDetail}>{correct_answers} aciertos de {total_questions}</Text>
          </View>

          {!passed ? (
            <View style={styles.notPassedBox}>
              <Text style={styles.notPassedTitle}>No aprobaste</Text>
              <Text style={styles.notPassedBody}>
                Necesitas 60% o más para ver el desglose. Intenta de nuevo para mejorar tu resultado.
              </Text>
            </View>
          ) : (
            <>
              <Text style={styles.sectionTitle}>Desglose por Especialidad</Text>
              {Object.entries(by_especialidad)
                .sort((a, b) => b[1].total - a[1].total)
                .map(([esp, data]) => {
                  const isOpen = expandedEsp[esp];
                  const temas = (temasByEsp[esp] ?? []).sort((a, b) => b.total - a.total);
                  const c = data.percentage >= 80 ? '#22C55E' : data.percentage >= 60 ? '#EAB308' : '#EF4444';
                  return (
                    <View key={esp} style={styles.espCard}>
                      <TouchableOpacity style={styles.espRow} onPress={() => setExpandedEsp(p => ({ ...p, [esp]: !p[esp] }))}>
                        <Text style={styles.espArrow}>{isOpen ? '▾' : '▸'}</Text>
                        <View style={styles.espInfo}>
                          <Text style={styles.espName}>{esp}</Text>
                          <Text style={styles.espDetail}>{data.correct}/{data.total} aciertos</Text>
                        </View>
                        <Text style={[styles.espPercent, { color: c }]}>{data.percentage}%</Text>
                      </TouchableOpacity>
                      {isOpen && temas.map((t, i) => {
                        const tc = t.percentage >= 80 ? '#22C55E' : t.percentage >= 60 ? '#EAB308' : '#EF4444';
                        return (
                          <View key={i} style={styles.temaRow}>
                            <Text style={styles.temaNombre}>{t.tema}</Text>
                            <Text style={[styles.temaPercent, { color: tc }]}>{t.percentage}%</Text>
                          </View>
                        );
                      })}
                    </View>
                  );
                })
              }
            </>
          )}

          <TouchableOpacity style={styles.btnBack} onPress={() => navigation.goBack()}>
            <Text style={styles.btnBackText}>Volver a Simulacros</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  if (!simulacro) return null;

  // ── Exam View ───────────────────────────────────────────────────────────────
  const questions = simulacro.questions;
  const q = questions[currentIndex];
  const answerKey = String(q.index);
  const isLowTime = timeRemaining < 600;

  return (
    <SafeAreaView style={styles.container}>
      {/* ENARM Header */}
      <View style={styles.examHeader}>
        <View style={styles.examHeaderLeft}>
          <View style={styles.examLogo}><Text style={styles.examLogoText}>E</Text></View>
          <Text style={styles.examTitle}>ENARM</Text>
        </View>
        <View style={styles.examHeaderRight}>
          <Text style={[styles.timer, isLowTime && styles.timerLow]}>{formatTime(timeRemaining)}</Text>
          <TouchableOpacity style={styles.finishBtn} onPress={() => setShowConfirmFinish(true)}>
            <Text style={styles.finishBtnText}>Finalizar</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Progress bar */}
      <View style={styles.progressRow}>
        <Text style={styles.progressText}>
          {currentIndex + 1}/{questions.length} · Contestadas: {Object.keys(answers).length}
        </Text>
        <TouchableOpacity style={styles.gridToggle} onPress={() => setShowGrid(true)}>
          <Text style={styles.gridToggleText}>🗒 Ver preguntas</Text>
        </TouchableOpacity>
      </View>

      {/* Question */}
      <ScrollView contentContainerStyle={styles.questionContent} showsVerticalScrollIndicator={false}>
        {!!q.case_text && (
          <View style={styles.caseBox}>
            <Text style={styles.caseLabel}>Caso Clínico{q.case_number ? ` ${q.case_number}` : ''}</Text>
            <Text style={styles.caseText}>{q.case_text}</Text>
          </View>
        )}
        <Text style={styles.questionText}>{q.question_text}</Text>

        {OPTIONS.map((opt) => {
          const key = `option_${opt.toLowerCase()}` as keyof Question;
          const text = q[key] as string;
          if (!text?.trim()) return null;
          const isSelected = answers[answerKey] === opt;
          return (
            <TouchableOpacity
              key={opt}
              style={[styles.option, isSelected && styles.optionSelected]}
              onPress={() => handleAnswer(opt)}
              activeOpacity={0.7}
            >
              <View style={[styles.radio, isSelected && styles.radioSelected]}>
                {isSelected && <View style={styles.radioInner} />}
              </View>
              <Text style={styles.optionText}><Text style={styles.optionLabel}>{opt})</Text> {text}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Bottom controls */}
      <View style={styles.bottomControls}>
        <TouchableOpacity style={[styles.navBtn, currentIndex === 0 && styles.navBtnOff]} disabled={currentIndex === 0} onPress={() => setCurrentIndex(i => i - 1)}>
          <Text style={styles.navBtnTxt}>‹ Ant</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.markBtn, marked.includes(currentIndex) && styles.markBtnActive]} onPress={toggleMark}>
          <Text style={styles.markBtnTxt}>{marked.includes(currentIndex) ? '🚩 Marcada' : '🏳 Marcar'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.navBtnNext, currentIndex === questions.length - 1 && styles.navBtnOff]} disabled={currentIndex === questions.length - 1} onPress={() => setCurrentIndex(i => i + 1)}>
          <Text style={styles.navBtnTxt}>Sig ›</Text>
        </TouchableOpacity>
      </View>

      {/* Question Grid Modal */}
      <Modal visible={showGrid} transparent animationType="slide">
        <TouchableOpacity style={styles.gridOverlay} activeOpacity={1} onPress={() => setShowGrid(false)}>
          <View style={styles.gridPanel}>
            <Text style={styles.gridTitle}>Preguntas</Text>
            <ScrollView>
              <View style={styles.gridItems}>
                {questions.map((_, i) => {
                  const qKey = String(questions[i].index);
                  const isAnswered = !!answers[qKey];
                  const isMarked = marked.includes(i);
                  const isCurrent = i === currentIndex;
                  let bg = '#1E293B';
                  if (isAnswered) bg = '#166534';
                  if (isMarked && !isAnswered) bg = '#854D0E';
                  if (isCurrent) bg = '#3730A3';
                  return (
                    <TouchableOpacity key={i} style={[styles.gridItem, { backgroundColor: bg }]}
                      onPress={() => { setCurrentIndex(i); setShowGrid(false); }}>
                      <Text style={styles.gridItemText}>{i + 1}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </ScrollView>
            <View style={styles.gridLegend}>
              <Text style={styles.legendItem}>🟢 Contestada</Text>
              <Text style={styles.legendItem}>🟡 Marcada</Text>
              <Text style={styles.legendItem}>⬜ Sin contestar</Text>
            </View>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Confirm Finish Modal */}
      <Modal visible={showConfirmFinish} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>¿Finalizar simulacro?</Text>
            <Text style={styles.modalBody}>
              Has contestado {Object.keys(answers).length} de {questions.length} preguntas.
              {Object.keys(answers).length < questions.length && `\n\nTienes ${questions.length - Object.keys(answers).length} preguntas sin contestar.`}
            </Text>
            <TouchableOpacity style={styles.btnDanger} onPress={() => handleFinish()}>
              <Text style={styles.btnDangerText}>Sí, finalizar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnCancel} onPress={() => setShowConfirmFinish(false)}>
              <Text style={styles.btnCancelText}>Continuar examen</Text>
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

  // Exam header
  examHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#1D4ED8', paddingHorizontal: 16, paddingVertical: 10 },
  examHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  examLogo: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#fff', justifyContent: 'center', alignItems: 'center' },
  examLogoText: { color: '#1D4ED8', fontWeight: 'bold', fontSize: 16 },
  examTitle: { color: '#fff', fontWeight: 'bold', fontSize: 18 },
  examHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  timer: { color: '#fff', fontSize: 22, fontFamily: 'monospace', fontWeight: 'bold' },
  timerLow: { color: '#FCA5A5' },
  finishBtn: { backgroundColor: '#DC2626', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6 },
  finishBtnText: { color: '#fff', fontWeight: '600', fontSize: 13 },

  // Progress
  progressRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 8, backgroundColor: '#1E293B' },
  progressText: { color: '#94A3B8', fontSize: 12 },
  gridToggle: { backgroundColor: '#1D4ED8', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6 },
  gridToggleText: { color: '#fff', fontSize: 12, fontWeight: '600' },

  // Question
  questionContent: { padding: 16, paddingBottom: 100 },
  caseBox: { backgroundColor: '#1E293B', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 3, borderLeftColor: '#1D4ED8' },
  caseLabel: { color: '#60A5FA', fontWeight: '700', fontSize: 13, marginBottom: 8 },
  caseText: { color: '#CBD5E1', fontSize: 14, lineHeight: 22 },
  questionText: { color: '#22C55E', fontSize: 16, fontWeight: '600', fontStyle: 'italic', lineHeight: 24, marginBottom: 16 },
  option: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#1E293B', borderRadius: 10, padding: 14, marginBottom: 8, borderWidth: 1.5, borderColor: '#334155', gap: 10 },
  optionSelected: { borderColor: '#1D4ED8', backgroundColor: '#172554' },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#475569', marginTop: 1, justifyContent: 'center', alignItems: 'center' },
  radioSelected: { borderColor: '#3B82F6' },
  radioInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#3B82F6' },
  optionLabel: { fontWeight: '700', color: '#94A3B8' },
  optionText: { flex: 1, color: '#CBD5E1', fontSize: 14, lineHeight: 21 },

  // Bottom controls
  bottomControls: { position: 'absolute', bottom: 0, left: 0, right: 0, flexDirection: 'row', backgroundColor: '#1E293B', borderTopWidth: 1, borderTopColor: '#334155', padding: 8, gap: 6 },
  navBtn: { flex: 1, backgroundColor: '#1D4ED8', borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  navBtnNext: { flex: 1, backgroundColor: '#2563EB', borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  navBtnOff: { opacity: 0.3 },
  navBtnTxt: { color: '#fff', fontWeight: '600', fontSize: 14 },
  markBtn: { flex: 1, backgroundColor: '#854D0E', borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  markBtnActive: { backgroundColor: '#EAB308' },
  markBtnTxt: { color: '#fff', fontWeight: '600', fontSize: 12 },

  // Grid
  gridOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  gridPanel: { backgroundColor: '#1E293B', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '75%' },
  gridTitle: { color: '#F8FAFC', fontWeight: 'bold', fontSize: 16, marginBottom: 16, textAlign: 'center' },
  gridItems: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  gridItem: { width: 36, height: 36, borderRadius: 6, justifyContent: 'center', alignItems: 'center' },
  gridItemText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  gridLegend: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#334155' },
  legendItem: { color: '#94A3B8', fontSize: 12 },

  // Results
  resultsContent: { padding: 0, paddingBottom: 40 },
  resultsHeader: { backgroundColor: '#1D4ED8', padding: 20, paddingTop: 40 },
  resultsHeaderTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  resultsHeaderSub: { color: '#BFDBFE', fontSize: 14, marginTop: 4 },
  scoreCard: { margin: 20, backgroundColor: '#1E293B', borderRadius: 16, padding: 28, alignItems: 'center', borderWidth: 2, gap: 8 },
  scorePercent: { fontSize: 56, fontWeight: 'bold' },
  scoreDetail: { color: '#94A3B8', fontSize: 16 },
  notPassedBox: { margin: 20, backgroundColor: '#2D0A0A', borderRadius: 16, padding: 20, borderWidth: 1, borderColor: '#7F1D1D', gap: 8 },
  notPassedTitle: { color: '#EF4444', fontSize: 18, fontWeight: 'bold' },
  notPassedBody: { color: '#94A3B8', fontSize: 14, lineHeight: 21 },
  sectionTitle: { color: '#F8FAFC', fontSize: 16, fontWeight: '600', paddingHorizontal: 20, marginBottom: 10 },
  espCard: { backgroundColor: '#1E293B', marginHorizontal: 20, marginBottom: 8, borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: '#334155' },
  espRow: { flexDirection: 'row', alignItems: 'center', padding: 14, gap: 10 },
  espArrow: { color: '#6366F1', fontSize: 16, width: 16 },
  espInfo: { flex: 1 },
  espName: { color: '#F8FAFC', fontWeight: '600', fontSize: 14 },
  espDetail: { color: '#64748B', fontSize: 12, marginTop: 2 },
  espPercent: { fontSize: 20, fontWeight: 'bold' },
  temaRow: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 10, borderTopWidth: 1, borderTopColor: '#334155', backgroundColor: '#0F172A' },
  temaNombre: { flex: 1, color: '#94A3B8', fontSize: 13 },
  temaPercent: { fontWeight: 'bold', fontSize: 13, marginLeft: 10 },
  btnBack: { backgroundColor: '#1D4ED8', borderRadius: 12, paddingVertical: 14, alignItems: 'center', margin: 20 },
  btnBackText: { color: '#fff', fontSize: 15, fontWeight: '600' },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalBox: { backgroundColor: '#1E293B', borderRadius: 20, padding: 24, width: '100%', borderWidth: 1, borderColor: '#334155', gap: 12 },
  modalTitle: { fontSize: 18, fontWeight: 'bold', color: '#F8FAFC' },
  modalBody: { fontSize: 14, color: '#94A3B8', lineHeight: 21 },
  btnDanger: { backgroundColor: '#DC2626', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  btnDangerText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnCancel: { backgroundColor: '#0F172A', borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  btnCancelText: { color: '#94A3B8', fontSize: 15 },
});
