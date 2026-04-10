import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, SafeAreaView,
  ActivityIndicator, ScrollView, Image, Alert, BackHandler,
  Animated,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'DuelGame'>;
  route: RouteProp<RootStackParamList, 'DuelGame'>;
};

interface DuelData {
  id: string;
  player1_id: string; player1_name: string; player1_image?: string;
  player1_score: number; player1_completed: boolean;
  player2_id: string; player2_name: string; player2_image?: string;
  player2_score: number; player2_completed: boolean;
  status: string;
  round_specialties: string[];
  round_questions: string[];
  question_source?: string;
  duel_topic?: string;
  winner_id?: string;
  challenger_message?: string;
}

interface Question {
  id: string;
  question_text: string;
  option_a: string; option_b: string; option_c: string; option_d?: string;
  correct_answer: string;
  explanation?: string;
  reference?: string;
  tema?: string;
}

const SPECIALTIES = [
  { name: 'Ginecología y Obstetricia', color: '#FF6B8A', emoji: '🤱' },
  { name: 'Cirugía', color: '#4ECDC4', emoji: '🔪' },
  { name: 'Pediatría', color: '#45B7D1', emoji: '👶' },
  { name: 'Medicina Interna', color: '#96CEB4', emoji: '🏥' },
  { name: 'Otros', color: '#FECA57', emoji: '📋' },
];

// ─── Spin Wheel (slot-machine style) ────────────────────────────────────────
function SpinWheel({ targetSpecialty, onComplete }: { targetSpecialty: string; onComplete: () => void }) {
  const [displayIdx, setDisplayIdx] = useState(0);
  const [spinning, setSpinning] = useState(false);
  const [done, setDone] = useState(false);
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const spin = useCallback(() => {
    if (spinning || done) return;

    const targetIdx = SPECIALTIES.findIndex(s => s.name === targetSpecialty);
    const target = targetIdx >= 0 ? targetIdx : 0;

    // Build sequence: rapid cycling → gradually reach target
    const seq: number[] = [];
    for (let i = 0; i < 18; i++) seq.push(i % 5);  // ~3.5 rotations rapid
    // Approach target from where we left off
    let cur = seq[seq.length - 1];
    while (cur !== target) {
      cur = (cur + 1) % 5;
      seq.push(cur);
    }

    const n = seq.length;
    const getDelay = (i: number): number => {
      const p = i / n;
      if (p < 0.55) return 70;
      if (p < 0.75) return 100 + (p - 0.55) * 600;
      return 220 + (p - 0.75) * 1400;
    };

    setSpinning(true);
    setDone(false);
    let step = 0;

    const advance = () => {
      setDisplayIdx(seq[step]);
      step++;
      if (step < seq.length) {
        setTimeout(advance, getDelay(step));
      } else {
        setTimeout(() => {
          setDone(true);
          setSpinning(false);
          Animated.sequence([
            Animated.spring(scaleAnim, { toValue: 1.12, useNativeDriver: true, tension: 200 }),
            Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true, tension: 200 }),
          ]).start(() => setTimeout(onComplete, 1200));
        }, 300);
      }
    };

    advance();
  }, [spinning, done, targetSpecialty, scaleAnim, onComplete]);

  const current = SPECIALTIES[displayIdx];

  return (
    <View style={wh.container}>
      <Text style={wh.label}>Gira para seleccionar especialidad</Text>

      <Animated.View style={[wh.card, { backgroundColor: current.color, transform: [{ scale: scaleAnim }] }]}>
        <Text style={wh.emoji}>{current.emoji}</Text>
        <Text style={wh.specialtyName}>{current.name}</Text>
      </Animated.View>

      <View style={wh.dots}>
        {SPECIALTIES.map((sp, i) => (
          <View key={i} style={[wh.dot, displayIdx === i && { backgroundColor: current.color, width: 20 }]} />
        ))}
      </View>

      {!done && (
        <TouchableOpacity
          style={[wh.spinBtn, spinning && wh.spinBtnDisabled]}
          onPress={spin}
          disabled={spinning}
        >
          <Text style={wh.spinBtnText}>{spinning ? 'GIRANDO...' : 'GIRAR'}</Text>
        </TouchableOpacity>
      )}

      {done && (
        <View style={wh.doneRow}>
          <Text style={wh.doneText}>¡{current.name}!</Text>
          <Text style={wh.doneSubtext}>Cargando pregunta...</Text>
        </View>
      )}
    </View>
  );
}

// ─── Main Screen ─────────────────────────────────────────────────────────────
type Phase = 'loading' | 'loadingQuestion' | 'wheel' | 'question' | 'feedback' | 'results' | 'waiting' | 'submitting';

export default function DuelGameScreen({ navigation, route }: Props) {
  const { duelId, opponentName: paramOpponentName, opponentImage: paramOpponentImage } = route.params;
  const { user } = useAuthStore();

  const [duel, setDuel] = useState<DuelData | null>(null);
  const [phase, setPhase] = useState<Phase>('loading');
  const [round, setRound] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [myScore, setMyScore] = useState<number | null>(null);
  const [finalResult, setFinalResult] = useState<'win' | 'lose' | 'tie' | null>(null);
  const [opponentFinalScore, setOpponentFinalScore] = useState<number | null>(null);

  // Keep round in a ref to avoid stale closure in callbacks
  const roundRef = useRef(0);
  const duelRef = useRef<DuelData | null>(null);
  useEffect(() => { roundRef.current = round; }, [round]);
  useEffect(() => { duelRef.current = duel; }, [duel]);

  // Block hardware back during game
  useEffect(() => {
    const handler = BackHandler.addEventListener('hardwareBackPress', () => {
      if (phase !== 'results' && phase !== 'waiting') {
        Alert.alert('¿Salir del duelo?', 'Perderás tu progreso en este duelo.', [
          { text: 'Seguir jugando', style: 'cancel' },
          { text: 'Salir', style: 'destructive', onPress: () => navigation.goBack() },
        ]);
        return true;
      }
      return false;
    });
    return () => handler.remove();
  }, [phase, navigation]);

  useEffect(() => {
    loadDuel();
  }, [duelId]);

  const loadDuel = async () => {
    try {
      const r = await api.get(`/api/duels/${duelId}`);
      const d: DuelData = r.data;
      setDuel(d);

      const isP1 = user?.id === d.player1_id;

      if (d.status === 'completed') {
        setPhase('results');
        const mine = isP1 ? d.player1_score : d.player2_score;
        const theirs = isP1 ? d.player2_score : d.player1_score;
        setMyScore(mine);
        setOpponentFinalScore(theirs);
        setFinalResult(mine > theirs ? 'win' : mine < theirs ? 'lose' : 'tie');
      } else if ((isP1 && d.status === 'waiting_player1') || (!isP1 && d.status === 'waiting_player2')) {
        setPhase('wheel');
      } else {
        setPhase('waiting');
      }
    } catch {
      Alert.alert('Error', 'No se pudo cargar el duelo');
      navigation.goBack();
    }
  };

  const loadQuestion = useCallback(async () => {
    const d = duelRef.current;
    const r = roundRef.current;
    if (!d) return;
    try {
      const qId = d.round_questions[r];
      const source = d.question_source;
      const endpoint = source === 'duel' ? `/api/duel-questions/${qId}` : `/api/questions/${qId}`;
      const res = await api.get(endpoint);
      setQuestion(res.data);
      setPhase('question');
    } catch {
      Alert.alert('Error', 'No se pudo cargar la pregunta');
    }
  }, []);

  const handleAnswer = (option: string) => {
    setSelected(option);
    setPhase('feedback');
  };

  const handleNext = () => {
    const newAnswers = [...answers, selected!];
    setAnswers(newAnswers);
    setSelected(null);
    setQuestion(null);

    const nextRound = round + 1;
    setRound(nextRound);
    roundRef.current = nextRound;

    if (nextRound < 5) {
      setPhase('wheel');
    } else {
      submitGame(newAnswers);
    }
  };

  const submitGame = async (finalAnswers: string[]) => {
    try {
      const r = await api.post('/api/duels/submit-game', {
        duel_id: duelId,
        answers: finalAnswers,
      });
      setMyScore(r.data.my_score);

      if (r.data.duel_completed) {
        const mine = r.data.my_score;
        const theirs = r.data.opponent_score;
        setOpponentFinalScore(theirs);
        setFinalResult(mine > theirs ? 'win' : mine < theirs ? 'lose' : 'tie');
      }

      setPhase('results');
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'Error al enviar respuestas');
    }
  };

  const exitDuel = () => {
    if (phase === 'results' || phase === 'waiting') {
      navigation.goBack();
    } else {
      Alert.alert('¿Salir del duelo?', 'Perderás tu progreso en este duelo.', [
        { text: 'Seguir jugando', style: 'cancel' },
        { text: 'Salir', style: 'destructive', onPress: () => navigation.goBack() },
      ]);
    }
  };

  if (!duel || phase === 'loading') {
    return <View style={s.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  const isP1 = user?.id === duel.player1_id;
  const myName = isP1 ? duel.player1_name : duel.player2_name;
  const myImage = isP1 ? duel.player1_image : duel.player2_image;
  const opponentName = paramOpponentName || (isP1 ? duel.player2_name : duel.player1_name);
  const opponentImage = paramOpponentImage || (isP1 ? duel.player2_image : duel.player1_image);

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={exitDuel} style={s.exitBtn}>
          <Text style={s.exitBtnText}>← Salir</Text>
        </TouchableOpacity>
        <Text style={s.roundLabel}>
          {phase === 'results' || phase === 'waiting' ? 'Duelo' : `Ronda ${round + 1} de 5`}
          {duel.duel_topic ? `\n${duel.duel_topic}` : ''}
        </Text>
        <View style={{ width: 60 }} />
      </View>

      {/* Players bar */}
      <View style={s.playersBar}>
        <View style={s.playerSide}>
          {myImage ? (
            <Image source={{ uri: myImage }} style={s.playerAvatar} />
          ) : (
            <View style={[s.playerAvatar, s.avatarFallback]}>
              <Text style={s.avatarInitial}>{myName.charAt(0).toUpperCase()}</Text>
            </View>
          )}
          <Text style={s.playerName} numberOfLines={1}>{myName}</Text>
          <Text style={s.playerLabel}>Tú</Text>
        </View>

        <Text style={s.vsLabel}>VS</Text>

        <View style={[s.playerSide, s.playerSideRight]}>
          <Text style={s.playerLabel}>Rival</Text>
          <Text style={s.playerName} numberOfLines={1}>{opponentName}</Text>
          {opponentImage ? (
            <Image source={{ uri: opponentImage }} style={s.playerAvatar} />
          ) : (
            <View style={[s.playerAvatar, s.avatarFallback]}>
              <Text style={s.avatarInitial}>{opponentName.charAt(0).toUpperCase()}</Text>
            </View>
          )}
        </View>
      </View>

      <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>

        {/* ── WHEEL PHASE ── */}
        {phase === 'wheel' && (
          <SpinWheel
            targetSpecialty={duel.round_specialties[round]}
            onComplete={loadQuestion}
          />
        )}

        {/* ── LOADING QUESTION ── */}
        {phase === 'loadingQuestion' && (
          <View style={s.centered}>
            <ActivityIndicator color="#6366F1" />
            <Text style={s.loadingText}>Cargando pregunta...</Text>
          </View>
        )}

        {/* ── QUESTION PHASE ── */}
        {(phase === 'question' || phase === 'feedback') && question && (
          <View style={s.card}>
            {/* Specialty badge */}
            <View style={s.specialtyBadge}>
              <Text style={s.specialtyBadgeText}>{duel.round_specialties[round]}</Text>
            </View>

            <Text style={s.questionText}>{question.question_text}</Text>

            <View style={s.options}>
              {(['A', 'B', 'C', 'D'] as const).map(opt => {
                const text = question[`option_${opt.toLowerCase()}` as keyof Question] as string | undefined;
                if (!text) return null;
                const isSelected = selected === opt;
                const isCorrect = question.correct_answer === opt;
                const showResult = phase === 'feedback';

                let style = s.option;
                if (showResult && isCorrect) style = s.optionCorrect;
                else if (showResult && isSelected && !isCorrect) style = s.optionWrong;
                else if (!showResult && isSelected) style = s.optionSelected;

                return (
                  <TouchableOpacity
                    key={opt}
                    style={style}
                    onPress={() => phase === 'question' && handleAnswer(opt)}
                    disabled={phase === 'feedback'}
                  >
                    <Text style={s.optionLetter}>{opt}.</Text>
                    <Text style={s.optionText}>{text}</Text>
                    {showResult && isCorrect && <Text style={s.optionMark}>✓</Text>}
                    {showResult && isSelected && !isCorrect && <Text style={s.optionMark}>✗</Text>}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Feedback */}
            {phase === 'feedback' && (
              <View style={[s.feedbackBox, selected === question.correct_answer ? s.feedbackCorrect : s.feedbackWrong]}>
                <Text style={s.feedbackTitle}>
                  {selected === question.correct_answer ? '✓  ¡Correcto!' : '✗  Incorrecto'}
                </Text>
                {question.explanation && (
                  <Text style={s.feedbackBody}>{question.explanation}</Text>
                )}
                {question.reference && (
                  <Text style={s.feedbackRef}>Ref: {question.reference}</Text>
                )}
                <TouchableOpacity style={s.nextBtn} onPress={handleNext}>
                  <Text style={s.nextBtnText}>
                    {round < 4 ? 'Siguiente Pregunta →' : 'Ver Resultados →'}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}

        {/* ── WAITING PHASE ── */}
        {phase === 'waiting' && (
          <View style={s.card}>
            <Text style={s.waitingEmoji}>⏳</Text>
            <Text style={s.waitingTitle}>Esperando al oponente...</Text>
            <Text style={s.waitingBody}>{opponentName} debe completar sus preguntas primero.</Text>
            <TouchableOpacity style={s.backBtn} onPress={() => navigation.goBack()}>
              <Text style={s.backBtnText}>Volver a Duelos</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── RESULTS PHASE ── */}
        {phase === 'results' && (
          <View style={s.card}>
            {finalResult ? (
              <>
                <View style={[s.resultBanner,
                  finalResult === 'win' && s.resultBannerWin,
                  finalResult === 'lose' && s.resultBannerLose,
                  finalResult === 'tie' && s.resultBannerTie,
                ]}>
                  <Text style={s.resultEmoji}>
                    {finalResult === 'win' ? '🏆' : finalResult === 'lose' ? '😔' : '🤝'}
                  </Text>
                  <Text style={[s.resultTitle,
                    finalResult === 'win' && { color: '#22C55E' },
                    finalResult === 'lose' && { color: '#EF4444' },
                    finalResult === 'tie' && { color: '#EAB308' },
                  ]}>
                    {finalResult === 'win' ? '¡GANASTE!' : finalResult === 'lose' ? '¡PERDISTE!' : '¡EMPATE!'}
                  </Text>
                  <View style={s.scoreSummary}>
                    <View style={s.scoreItem}>
                      <Text style={s.scoreLabel}>Tú</Text>
                      <Text style={s.scoreNumber}>{myScore}</Text>
                    </View>
                    <Text style={s.scoreDash}>—</Text>
                    <View style={s.scoreItem}>
                      <Text style={s.scoreLabel}>{opponentName}</Text>
                      <Text style={s.scoreNumber}>{opponentFinalScore}</Text>
                    </View>
                  </View>
                </View>
              </>
            ) : (
              <>
                <Text style={s.waitingEmoji}>
                  {myScore !== null && myScore >= 4 ? '🏆' : myScore !== null && myScore >= 3 ? '👍' : '💪'}
                </Text>
                <Text style={s.waitingTitle}>¡Completaste el duelo!</Text>
                <Text style={[s.myScoreDisplay,
                  myScore !== null && myScore >= 4 ? { color: '#22C55E' } :
                  myScore !== null && myScore >= 3 ? { color: '#EAB308' } : { color: '#EF4444' }
                ]}>
                  {myScore}/5
                </Text>
                <Text style={s.waitingBody}>Esperando a que {opponentName} complete sus preguntas...</Text>
              </>
            )}

            {/* Challenger message */}
            {duel.challenger_message && (
              <View style={s.messageBox}>
                <Text style={s.messageBoxLabel}>Mensaje del retador:</Text>
                <Text style={s.messageBoxText}>"{duel.challenger_message}"</Text>
              </View>
            )}

            <TouchableOpacity style={s.backBtn} onPress={() => navigation.goBack()}>
              <Text style={s.backBtnText}>Volver a Duelos</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── SpinWheel styles ─────────────────────────────────────────────────────────
const wh = StyleSheet.create({
  container: { alignItems: 'center', paddingVertical: 20, gap: 16 },
  label: { fontSize: 14, color: '#94A3B8', textAlign: 'center' },
  card: {
    width: 240, height: 160, borderRadius: 20, justifyContent: 'center', alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
    gap: 8,
  },
  emoji: { fontSize: 36 },
  specialtyName: { fontSize: 18, fontWeight: 'bold', color: '#fff', textAlign: 'center', paddingHorizontal: 12, textShadowColor: 'rgba(0,0,0,0.3)', textShadowOffset: { width: 1, height: 1 }, textShadowRadius: 2 },
  dots: { flexDirection: 'row', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#334155' },
  spinBtn: {
    backgroundColor: '#F59E0B', borderRadius: 14, paddingVertical: 14, paddingHorizontal: 40,
    shadowColor: '#F59E0B', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 8, elevation: 6,
  },
  spinBtnDisabled: { backgroundColor: '#475569', shadowOpacity: 0 },
  spinBtnText: { fontSize: 18, fontWeight: 'black', color: '#fff', letterSpacing: 1 },
  doneRow: { alignItems: 'center', gap: 4 },
  doneText: { fontSize: 16, fontWeight: 'bold', color: '#F8FAFC' },
  doneSubtext: { fontSize: 12, color: '#64748B' },
});

// ─── Screen styles ─────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  loadingText: { color: '#64748B', fontSize: 14 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12,
    backgroundColor: '#1E293B', borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  exitBtn: { paddingHorizontal: 4 },
  exitBtnText: { color: '#94A3B8', fontSize: 14 },
  roundLabel: { fontSize: 14, fontWeight: 'bold', color: '#F8FAFC', textAlign: 'center' },
  playersBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12,
    backgroundColor: '#1E293B', borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  playerSide: { flex: 1, alignItems: 'flex-start', gap: 2 },
  playerSideRight: { alignItems: 'flex-end' },
  playerAvatar: { width: 44, height: 44, borderRadius: 22 },
  avatarFallback: { backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' },
  avatarInitial: { color: '#F8FAFC', fontSize: 16, fontWeight: 'bold' },
  playerName: { fontSize: 12, fontWeight: '600', color: '#F8FAFC', maxWidth: 100 },
  playerLabel: { fontSize: 10, color: '#64748B' },
  vsLabel: { fontSize: 22, fontWeight: 'bold', color: '#475569', paddingHorizontal: 8 },
  content: { padding: 16, paddingBottom: 40 },
  card: { backgroundColor: '#1E293B', borderRadius: 20, padding: 20, borderWidth: 1, borderColor: '#334155', gap: 14 },
  specialtyBadge: { backgroundColor: '#312E81', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, alignSelf: 'flex-start' },
  specialtyBadgeText: { color: '#A5B4FC', fontSize: 12, fontWeight: '600' },
  questionText: { fontSize: 16, color: '#F8FAFC', lineHeight: 24, fontWeight: '500' },
  options: { gap: 8 },
  option: {
    flexDirection: 'row', alignItems: 'center', padding: 14,
    backgroundColor: '#0F172A', borderRadius: 12, borderWidth: 1.5, borderColor: '#334155', gap: 10,
  },
  optionSelected: {
    flexDirection: 'row', alignItems: 'center', padding: 14,
    backgroundColor: '#1D2F5A', borderRadius: 12, borderWidth: 1.5, borderColor: '#3B82F6', gap: 10,
  },
  optionCorrect: {
    flexDirection: 'row', alignItems: 'center', padding: 14,
    backgroundColor: '#052E16', borderRadius: 12, borderWidth: 1.5, borderColor: '#22C55E', gap: 10,
  },
  optionWrong: {
    flexDirection: 'row', alignItems: 'center', padding: 14,
    backgroundColor: '#2D0A0A', borderRadius: 12, borderWidth: 1.5, borderColor: '#EF4444', gap: 10,
  },
  optionLetter: { fontSize: 15, fontWeight: 'bold', color: '#6366F1', width: 22 },
  optionText: { flex: 1, fontSize: 14, color: '#E2E8F0', lineHeight: 20 },
  optionMark: { fontSize: 18 },
  feedbackBox: { borderRadius: 14, padding: 16, gap: 8, borderWidth: 1 },
  feedbackCorrect: { backgroundColor: '#052E16', borderColor: '#22C55E' },
  feedbackWrong: { backgroundColor: '#2D0A0A', borderColor: '#EF4444' },
  feedbackTitle: { fontSize: 16, fontWeight: 'bold', color: '#F8FAFC' },
  feedbackBody: { fontSize: 13, color: '#94A3B8', lineHeight: 20 },
  feedbackRef: { fontSize: 11, color: '#475569', fontStyle: 'italic' },
  nextBtn: { backgroundColor: '#6366F1', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginTop: 4 },
  nextBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },

  // Waiting / Results
  waitingEmoji: { fontSize: 64, textAlign: 'center' },
  waitingTitle: { fontSize: 20, fontWeight: 'bold', color: '#F8FAFC', textAlign: 'center' },
  waitingBody: { fontSize: 14, color: '#64748B', textAlign: 'center', lineHeight: 20 },
  myScoreDisplay: { fontSize: 52, fontWeight: 'bold', textAlign: 'center' },
  resultBanner: { borderRadius: 16, padding: 20, alignItems: 'center', gap: 10, borderWidth: 2 },
  resultBannerWin: { backgroundColor: '#052E16', borderColor: '#22C55E' },
  resultBannerLose: { backgroundColor: '#2D0A0A', borderColor: '#EF4444' },
  resultBannerTie: { backgroundColor: '#1C1A07', borderColor: '#EAB308' },
  resultEmoji: { fontSize: 56 },
  resultTitle: { fontSize: 32, fontWeight: 'black', letterSpacing: 1 },
  scoreSummary: { flexDirection: 'row', alignItems: 'center', gap: 16, marginTop: 4 },
  scoreItem: { alignItems: 'center', gap: 2 },
  scoreLabel: { fontSize: 12, color: '#94A3B8' },
  scoreNumber: { fontSize: 36, fontWeight: 'bold', color: '#F8FAFC' },
  scoreDash: { fontSize: 22, color: '#475569' },
  messageBox: { backgroundColor: '#0F172A', borderRadius: 10, padding: 12, borderWidth: 1, borderColor: '#334155' },
  messageBoxLabel: { fontSize: 11, color: '#64748B', marginBottom: 4 },
  messageBoxText: { fontSize: 13, color: '#94A3B8', fontStyle: 'italic' },
  backBtn: { backgroundColor: '#1E293B', borderRadius: 12, paddingVertical: 13, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  backBtnText: { color: '#94A3B8', fontSize: 14, fontWeight: '600' },
});
