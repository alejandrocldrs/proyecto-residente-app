import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'FlashcardTopics'>;
  route: RouteProp<RootStackParamList, 'FlashcardTopics'>;
};

export default function FlashcardTopicsScreen({ navigation, route }: Props) {
  const { specialty } = route.params;
  const [topics, setTopics] = useState<Record<string, { count: number }>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/flashcards/grouped')
      .then(r => setTopics(r.data[specialty]?.topics ?? {}))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [specialty]);

  const topicNames = Object.keys(topics);
  const totalCards = Object.values(topics).reduce((sum, t) => sum + (t.count ?? 0), 0);

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>{specialty}</Text>
        <Text style={styles.subtitle}>{totalCards} tarjetas en total</Text>

        {topicNames.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No hay subtemas con flashcards</Text>
          </View>
        ) : (
          topicNames.map((topic) => {
            const count = topics[topic]?.count ?? 0;
            return (
              <TouchableOpacity
                key={topic}
                style={styles.item}
                onPress={() => navigation.navigate('FlashcardDecks', { specialty, topic })}
                activeOpacity={0.7}
              >
                <View style={styles.dot} />
                <View style={styles.itemContent}>
                  <Text style={styles.itemTitle}>{topic}</Text>
                  <Text style={styles.itemCount}>{count} {count === 1 ? 'tarjeta' : 'tarjetas'}</Text>
                </View>
                <Text style={styles.chevron}>›</Text>
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
  title: { fontSize: 22, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#64748B', marginBottom: 24 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: '#64748B', fontSize: 15 },
  item: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: '#1E293B',
  },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#6366F1', marginRight: 14 },
  itemContent: { flex: 1 },
  itemTitle: { fontSize: 15, color: '#E2E8F0', fontWeight: '500' },
  itemCount: { fontSize: 12, color: '#64748B', marginTop: 2 },
  chevron: { fontSize: 22, color: '#475569' },
});
