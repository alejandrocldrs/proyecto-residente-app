import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Topics'>;
  route: RouteProp<RootStackParamList, 'Topics'>;
};

interface Quiz {
  id: string;
  topic: string;
  questions: any[];
}

export default function TopicsScreen({ navigation, route }: Props) {
  const { specialty, submodule } = route.params;
  const effectiveSpecialty = submodule ? `${specialty} - ${submodule}` : specialty;

  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [passedQuizzes, setPassedQuizzes] = useState<string[]>([]);
  const [passCounts, setPassCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    Promise.all([fetchQuizzes(), fetchProgress(), fetchPassCounts()]);
  }, [effectiveSpecialty]);

  const fetchQuizzes = async () => {
    try {
      const res = await api.get(`/api/quizzes?specialty=${encodeURIComponent(effectiveSpecialty)}`);
      setQuizzes(res.data);
    } catch {
      Alert.alert('Error', 'No se pudieron cargar los temas');
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const res = await api.get('/api/progress/quizzes');
      setPassedQuizzes(res.data.passed ?? []);
    } catch {}
  };

  const fetchPassCounts = async () => {
    try {
      const res = await api.get('/api/progress/pass-counts');
      setPassCounts(res.data.pass_counts ?? {});
    } catch {}
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#6366F1" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>{submodule ?? specialty}</Text>
        {submodule && <Text style={styles.subtitle}>{specialty}</Text>}

        {quizzes.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No hay temas disponibles aún</Text>
          </View>
        ) : (
          quizzes.map((quiz) => {
            const passed = passedQuizzes.includes(quiz.id);
            const count = passCounts[quiz.id] ?? 0;

            return (
              <TouchableOpacity
                key={quiz.id}
                style={[styles.card, passed && styles.cardPassed]}
                onPress={() => navigation.navigate('Quiz', { quizId: quiz.id })}
                activeOpacity={0.7}
              >
                {/* Pass count badge */}
                {count > 0 && (
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{count}</Text>
                  </View>
                )}

                {/* Left indicator dot */}
                <View style={[styles.indicator, passed && styles.indicatorPassed]} />

                {/* Content */}
                <View style={styles.cardBody}>
                  <Text style={[styles.cardTitle, passed && styles.cardTitlePassed]}>
                    {quiz.topic}
                  </Text>
                  <Text style={styles.cardCount}>{quiz.questions.length} preguntas</Text>
                </View>

                {/* Right icon */}
                <Text style={[styles.chevron, passed && styles.checkmark]}>
                  {passed ? '✓' : '›'}
                </Text>
              </TouchableOpacity>
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
  title: { fontSize: 22, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 2 },
  subtitle: { fontSize: 13, color: '#64748B', marginBottom: 20 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#64748B', fontSize: 15 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardPassed: { borderColor: '#1E3A2F', backgroundColor: '#162820' },
  badge: {
    position: 'absolute',
    top: -8,
    right: -8,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
  },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  indicator: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: '#475569',
    marginRight: 14,
  },
  indicatorPassed: { borderColor: '#22C55E', backgroundColor: '#22C55E' },
  cardBody: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#E2E8F0', marginBottom: 3 },
  cardTitlePassed: { color: '#64748B' },
  cardCount: { fontSize: 12, color: '#64748B' },
  chevron: { fontSize: 22, color: '#475569', marginLeft: 8 },
  checkmark: { color: '#22C55E', fontWeight: 'bold' },
});
