import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Image,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';

type Props = { navigation: NativeStackNavigationProp<RootStackParamList, 'Leaderboard'> };

interface RankingEntry {
  user_id: string;
  full_name: string;
  profile_image?: string;
  rank_name?: string;
  score: number;
  quiz_count: number;
  simulacro_count: number;
  escape_room_count: number;
  duel_win_count: number;
  imagendx_count: number;
}

export default function LeaderboardScreen({ navigation }: Props) {
  const { user } = useAuthStore();
  const [rankings, setRankings] = useState<RankingEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRanking = async () => {
    setLoading(true);
    try {
      const r = await api.get('/api/ranking/daily-top10');
      setRankings(r.data);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { fetchRanking(); }, []);

  const rankEmoji = (pos: number) => {
    if (pos === 1) return '🥇';
    if (pos === 2) return '🥈';
    if (pos === 3) return '🥉';
    return `#${pos}`;
  };

  if (loading) {
    return <View style={s.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
        <Text style={s.title}>Ranking del Día</Text>
        <Text style={s.subtitle}>Se reinicia a las 9:00 PM</Text>

        <View style={s.legend}>
          {['Cuestionario ×25', 'Simulacro ×50', 'Duelo ×5'].map(f => (
            <Text key={f} style={s.legendItem}>{f}</Text>
          ))}
        </View>

        {rankings.length === 0 ? (
          <View style={s.empty}>
            <Text style={s.emptyEmoji}>🏆</Text>
            <Text style={s.emptyText}>Sin actividad hoy</Text>
            <Text style={s.emptySub}>¡Sé el primero en sumar puntos!</Text>
          </View>
        ) : (
          rankings.map((entry, index) => {
            const pos = index + 1;
            const isMe = entry.user_id === user?.id;
            const details = [
              entry.quiz_count > 0 && `${entry.quiz_count} cuest.`,
              entry.simulacro_count > 0 && `${entry.simulacro_count} sim.`,
              entry.duel_win_count > 0 && `${entry.duel_win_count} duelos`,
            ].filter(Boolean).join(' · ');

            return (
              <View key={entry.user_id} style={[s.entry, isMe && s.entryMe]}>
                <Text style={s.rank}>{rankEmoji(pos)}</Text>

                {entry.profile_image ? (
                  <Image source={{ uri: entry.profile_image }} style={s.avatar} />
                ) : (
                  <View style={[s.avatar, s.avatarFallback]}>
                    <Text style={s.avatarInitial}>{entry.full_name.charAt(0).toUpperCase()}</Text>
                  </View>
                )}

                <View style={s.info}>
                  <View style={s.nameRow}>
                    <Text style={s.name} numberOfLines={1}>{entry.full_name}</Text>
                    {isMe && <Text style={s.youBadge}>Tú</Text>}
                  </View>
                  {!!entry.rank_name && <Text style={s.rankName}>{entry.rank_name}</Text>}
                  {!!details && <Text style={s.details}>{details}</Text>}
                </View>

                <View style={s.scoreCol}>
                  <Text style={s.score}>{entry.score.toLocaleString()}</Text>
                  <Text style={s.pts}>pts</Text>
                </View>
              </View>
            );
          })
        )}

        <TouchableOpacity style={s.refreshBtn} onPress={fetchRanking}>
          <Text style={s.refreshBtnText}>↻  Actualizar</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#F8FAFC', textAlign: 'center', marginBottom: 4 },
  subtitle: { fontSize: 12, color: '#64748B', textAlign: 'center', marginBottom: 12 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'center', marginBottom: 20 },
  legendItem: { fontSize: 11, color: '#475569', backgroundColor: '#1E293B', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 8 },
  emptyEmoji: { fontSize: 48 },
  emptyText: { fontSize: 16, color: '#94A3B8', fontWeight: '500' },
  emptySub: { fontSize: 13, color: '#475569' },
  entry: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1E293B', borderRadius: 12,
    padding: 12, marginBottom: 8,
    borderWidth: 1, borderColor: '#334155', gap: 10,
  },
  entryMe: { borderColor: '#6366F1', borderWidth: 2 },
  rank: { fontSize: 20, width: 36, textAlign: 'center', color: '#F8FAFC' },
  avatar: { width: 40, height: 40, borderRadius: 20 },
  avatarFallback: { backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' },
  avatarInitial: { color: '#F8FAFC', fontSize: 16, fontWeight: 'bold' },
  info: { flex: 1, gap: 2 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  name: { fontSize: 14, fontWeight: '600', color: '#F8FAFC', flex: 1 },
  youBadge: { fontSize: 10, color: '#6366F1', fontWeight: '700', borderWidth: 1, borderColor: '#6366F1', paddingHorizontal: 5, paddingVertical: 2, borderRadius: 5 },
  rankName: { fontSize: 11, color: '#94A3B8' },
  details: { fontSize: 11, color: '#475569' },
  scoreCol: { alignItems: 'flex-end' },
  score: { fontSize: 18, fontWeight: 'bold', color: '#F8FAFC' },
  pts: { fontSize: 10, color: '#64748B' },
  refreshBtn: { marginTop: 20, alignSelf: 'center', backgroundColor: '#1E293B', borderRadius: 10, paddingVertical: 10, paddingHorizontal: 24, borderWidth: 1, borderColor: '#334155' },
  refreshBtnText: { color: '#94A3B8', fontSize: 14 },
});
