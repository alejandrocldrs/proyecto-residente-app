import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Simulacros'>;
};

interface Simulacro {
  id: string;
  title: string;
  total_questions: number;
  total_cases: number;
  user_attempt?: {
    status: 'in_progress' | 'completed';
    score: number;
    total_questions: number;
  };
}

export default function SimulacrosScreen({ navigation }: Props) {
  const [simulacros, setSimulacros] = useState<Simulacro[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/simulacros')
      .then(r => setSimulacros(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Simulacros</Text>
        <Text style={styles.subtitle}>Exámenes tipo ENARM · 280 preguntas · 5 horas</Text>

        {simulacros.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>📝</Text>
            <Text style={styles.emptyText}>No hay simulacros disponibles</Text>
            <Text style={styles.emptySub}>El administrador debe cargar un simulacro</Text>
          </View>
        ) : (
          simulacros.map((sim) => {
            const attempt = sim.user_attempt;
            const isCompleted = attempt?.status === 'completed';
            const isInProgress = attempt?.status === 'in_progress';
            const scorePercent = isCompleted && attempt
              ? Math.round((attempt.score / attempt.total_questions) * 100)
              : null;
            const passed = scorePercent !== null && scorePercent >= 60;

            return (
              <View key={sim.id} style={styles.card}>
                <Text style={styles.cardTitle}>{sim.title}</Text>
                <View style={styles.cardMeta}>
                  <Text style={styles.metaItem}>📋 {sim.total_questions} preguntas</Text>
                  <Text style={styles.metaItem}>⏱ 5 horas</Text>
                  <Text style={styles.metaItem}>🏥 {sim.total_cases} casos</Text>
                </View>

                {/* Status badge */}
                {isCompleted && scorePercent !== null && (
                  <View style={[styles.statusBadge, passed ? styles.badgePassed : styles.badgeFailed]}>
                    <Text style={[styles.statusText, passed ? styles.statusPassed : styles.statusFailed]}>
                      {passed ? '✓ Aprobado' : '✗ No aprobado'} — {attempt!.score}/{attempt!.total_questions} ({scorePercent}%)
                    </Text>
                  </View>
                )}
                {isInProgress && (
                  <View style={[styles.statusBadge, styles.badgeInProgress]}>
                    <Text style={styles.statusInProgress}>⏳ En progreso</Text>
                  </View>
                )}

                {/* Actions */}
                <View style={styles.cardActions}>
                  {isCompleted && passed && (
                    <TouchableOpacity
                      style={styles.btnSecondary}
                      onPress={() => navigation.navigate('SimulacroExam', { simulacroId: sim.id, viewResults: true })}
                    >
                      <Text style={styles.btnSecondaryText}>Ver resultados</Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={[styles.btnPrimary, isInProgress && styles.btnInProgress]}
                    onPress={() => navigation.navigate('SimulacroExam', { simulacroId: sim.id, viewResults: false })}
                  >
                    <Text style={styles.btnPrimaryText}>
                      {isInProgress ? '▶ Continuar' : '▶ Iniciar'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#64748B', marginBottom: 24 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 10 },
  emptyEmoji: { fontSize: 48 },
  emptyText: { fontSize: 16, color: '#94A3B8', fontWeight: '500' },
  emptySub: { fontSize: 13, color: '#475569', textAlign: 'center' },
  card: { backgroundColor: '#1E293B', borderRadius: 16, padding: 20, marginBottom: 14, borderWidth: 1, borderColor: '#334155', gap: 12 },
  cardTitle: { fontSize: 17, fontWeight: 'bold', color: '#F8FAFC' },
  cardMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  metaItem: { fontSize: 13, color: '#94A3B8' },
  statusBadge: { borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12 },
  badgePassed: { backgroundColor: '#052E16' },
  badgeFailed: { backgroundColor: '#2D0A0A' },
  badgeInProgress: { backgroundColor: '#1C1A07' },
  statusText: { fontSize: 13, fontWeight: '600' },
  statusPassed: { color: '#22C55E' },
  statusFailed: { color: '#EF4444' },
  statusInProgress: { color: '#EAB308', fontSize: 13, fontWeight: '600' },
  cardActions: { flexDirection: 'row', gap: 10 },
  btnPrimary: { flex: 1, backgroundColor: '#1D4ED8', borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  btnInProgress: { backgroundColor: '#D97706' },
  btnPrimaryText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  btnSecondary: { flex: 1, backgroundColor: '#1E293B', borderRadius: 10, paddingVertical: 12, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  btnSecondaryText: { color: '#94A3B8', fontSize: 14 },
});
