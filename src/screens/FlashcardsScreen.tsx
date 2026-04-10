import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { specialtyEmoji } from '../data/specialtyStructure';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Flashcards'>;
};

const SPECIALTIES = ['Ginecología y Obstetricia','Cirugía','Pediatría','Medicina Interna','Otros'];

interface GroupedData {
  [specialty: string]: { count: number; topics: Record<string, unknown> };
}

export default function FlashcardsScreen({ navigation }: Props) {
  const [groupedData, setGroupedData] = useState<GroupedData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/flashcards/grouped')
      .then(r => setGroupedData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalCards = Object.values(groupedData).reduce((sum, s) => sum + (s.count ?? 0), 0);

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Flash Cards</Text>
        <Text style={styles.subtitle}>{totalCards} {totalCards === 1 ? 'tarjeta' : 'tarjetas'} guardadas</Text>

        {totalCards === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>🃏</Text>
            <Text style={styles.emptyText}>No tienes flashcards guardadas</Text>
            <Text style={styles.emptySub}>Guarda preguntas desde los cuestionarios</Text>
          </View>
        ) : (
          SPECIALTIES.map((specialty) => {
            const count = groupedData[specialty]?.count ?? 0;
            const hasCards = count > 0;
            return (
              <TouchableOpacity
                key={specialty}
                style={[styles.card, !hasCards && styles.cardDisabled]}
                onPress={() => hasCards && navigation.navigate('FlashcardTopics', { specialty })}
                disabled={!hasCards}
                activeOpacity={0.7}
              >
                <Text style={styles.cardEmoji}>{specialtyEmoji[specialty] ?? '📚'}</Text>
                <View style={styles.cardContent}>
                  <Text style={[styles.cardTitle, !hasCards && styles.textDim]}>{specialty}</Text>
                  <Text style={styles.cardCount}>{count} {count === 1 ? 'tarjeta' : 'tarjetas'}</Text>
                </View>
                {hasCards && <Text style={styles.chevron}>›</Text>}
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
  title: { fontSize: 26, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#64748B', marginBottom: 24 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 8 },
  emptyEmoji: { fontSize: 48 },
  emptyText: { fontSize: 16, color: '#94A3B8', fontWeight: '500' },
  emptySub: { fontSize: 13, color: '#475569', textAlign: 'center' },
  card: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#1E293B',
    borderRadius: 16, padding: 18, marginBottom: 10, borderWidth: 1, borderColor: '#334155',
  },
  cardDisabled: { opacity: 0.4 },
  cardEmoji: { fontSize: 32, marginRight: 14 },
  cardContent: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#F8FAFC', marginBottom: 3 },
  textDim: { color: '#475569' },
  cardCount: { fontSize: 12, color: '#64748B' },
  chevron: { fontSize: 24, color: '#475569' },
});
