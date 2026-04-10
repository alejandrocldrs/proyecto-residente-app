import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, TextInput, Image,
  FlatList, Alert, Modal,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { useAuthStore } from '../store/authStore';
import api from '../services/api';

type Props = { navigation: NativeStackNavigationProp<RootStackParamList, 'Duels'> };
type Tab = 'lobby' | 'pending' | 'completed';

interface ActiveUser { id: string; full_name: string; email: string; profile_image?: string; }

interface PendingDuel {
  id: string;
  challenger_id: string;
  challenger_name: string;
  challenger_image?: string;
  status_message: string;
  created_at: string;
  challenger_message?: string;
  duel_topic?: string;
}

interface CompletedDuel {
  id: string;
  player1_id: string;
  player1_name: string;
  player1_image?: string;
  player1_score: number;
  player2_id: string;
  player2_name: string;
  player2_image?: string;
  player2_score: number;
  winner_id?: string;
  result_message: string;
  challenger_message?: string;
  winner_message?: string;
}

const TOPICS = [
  { label: 'Cualquier tema', value: '' },
  { label: 'Gine y Obste', value: 'Ginecología y Obstetricia' },
  { label: 'Cirugía', value: 'Cirugía' },
  { label: 'Pediatría', value: 'Pediatría' },
  { label: 'Med. Interna', value: 'Medicina Interna' },
  { label: 'Otros', value: 'Otros' },
];

export default function DuelsScreen({ navigation }: Props) {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>('lobby');

  // Challenge form
  const [showChallengeForm, setShowChallengeForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserList, setShowUserList] = useState(false);
  const [users, setUsers] = useState<ActiveUser[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ActiveUser | null>(null);
  const [message, setMessage] = useState('');
  const [topic, setTopic] = useState('');
  const [sendingChallenge, setSendingChallenge] = useState(false);

  // Lists
  const [pendingDuels, setPendingDuels] = useState<PendingDuel[]>([]);
  const [completedDuels, setCompletedDuels] = useState<CompletedDuel[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchData = useCallback(async () => {
    setLoadingData(true);
    try {
      const [pendingRes, completedRes] = await Promise.allSettled([
        api.get('/api/duels/pending'),
        api.get('/api/duels/completed?page=1&page_size=50'),
      ]);
      if (pendingRes.status === 'fulfilled') setPendingDuels(pendingRes.value.data || []);
      if (completedRes.status === 'fulfilled') {
        const d = completedRes.value.data;
        setCompletedDuels(d?.duels || d || []);
      }
    } catch {}
    finally { setLoadingData(false); }
  }, []);

  useFocusEffect(useCallback(() => { fetchData(); }, [fetchData]));

  const fetchUsers = async (q: string) => {
    setLoadingUsers(true);
    try {
      const endpoint = q.length >= 2
        ? `/api/users/search?q=${encodeURIComponent(q)}&limit=20`
        : '/api/users/active?limit=20';
      const r = await api.get(endpoint);
      setUsers(r.data || []);
    } catch {}
    finally { setLoadingUsers(false); }
  };

  const handleSearchChange = (text: string) => {
    setSearchQuery(text);
    setSelectedUser(null);
    setShowUserList(true);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => fetchUsers(text), 300);
  };

  const selectUser = (u: ActiveUser) => {
    setSelectedUser(u);
    setSearchQuery(u.full_name);
    setShowUserList(false);
  };

  const sendChallenge = async () => {
    if (!selectedUser) { Alert.alert('Selecciona un usuario'); return; }
    setSendingChallenge(true);
    try {
      const r = await api.post('/api/duels/challenge', {
        player2_email: selectedUser.email,
        challenger_message: message.trim() || null,
        duel_topic: topic || null,
      });
      const duelId = r.data.duel_id;
      setShowChallengeForm(false);
      setSelectedUser(null);
      setSearchQuery('');
      setMessage('');
      setTopic('');
      navigation.navigate('DuelGame', {
        duelId,
        opponentName: selectedUser.full_name,
        opponentImage: selectedUser.profile_image,
      });
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'No se pudo crear el duelo');
    } finally { setSendingChallenge(false); }
  };

  const acceptDuel = (duel: PendingDuel) => {
    navigation.navigate('DuelGame', {
      duelId: duel.id,
      opponentName: duel.challenger_name,
      opponentImage: duel.challenger_image,
    });
  };

  const rejectDuel = async (duelId: string) => {
    try {
      await api.post(`/api/duels/reject/${duelId}`);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'No se pudo rechazar el duelo');
    }
  };

  return (
    <SafeAreaView style={s.container}>
      {/* Tab bar */}
      <View style={s.tabBar}>
        {([
          { id: 'lobby', label: '👥 Lobby' },
          { id: 'pending', label: `⏳ Retos (${pendingDuels.length})` },
          { id: 'completed', label: `🏆 Historial (${completedDuels.length})` },
        ] as { id: Tab; label: string }[]).map(tab => (
          <TouchableOpacity
            key={tab.id}
            style={[s.tab, activeTab === tab.id && s.tabActive]}
            onPress={() => setActiveTab(tab.id)}
          >
            <Text style={[s.tabText, activeTab === tab.id && s.tabTextActive]} numberOfLines={1}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* ── LOBBY TAB ── */}
      {activeTab === 'lobby' && (
        <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
          <Text style={s.sectionTitle}>Retar a un Compañero</Text>

          {!showChallengeForm ? (
            <TouchableOpacity
              style={s.challengeBtn}
              onPress={() => { setShowChallengeForm(true); fetchUsers(''); setShowUserList(true); }}
            >
              <Text style={s.challengeBtnText}>⚔️  Retar Usuario</Text>
            </TouchableOpacity>
          ) : (
            <View style={s.form}>
              {/* User search */}
              <Text style={s.label}>Selecciona un usuario</Text>
              <View>
                <TextInput
                  style={s.input}
                  placeholder="Buscar por nombre..."
                  placeholderTextColor="#475569"
                  value={searchQuery}
                  onChangeText={handleSearchChange}
                  onFocus={() => { setShowUserList(true); if (users.length === 0) fetchUsers(''); }}
                />
                {showUserList && (
                  <View style={s.dropdown}>
                    {loadingUsers ? (
                      <View style={s.dropdownLoading}>
                        <ActivityIndicator size="small" color="#6366F1" />
                        <Text style={s.dropdownLoadingText}>Cargando...</Text>
                      </View>
                    ) : users.length === 0 ? (
                      <Text style={s.dropdownEmpty}>No se encontraron usuarios</Text>
                    ) : (
                      users.map(u => (
                        <TouchableOpacity
                          key={u.id}
                          style={[s.dropdownItem, selectedUser?.id === u.id && s.dropdownItemSelected]}
                          onPress={() => selectUser(u)}
                        >
                          {u.profile_image ? (
                            <Image source={{ uri: u.profile_image }} style={s.userAvatar} />
                          ) : (
                            <View style={[s.userAvatar, s.userAvatarFallback]}>
                              <Text style={s.userAvatarInitial}>{u.full_name.charAt(0).toUpperCase()}</Text>
                            </View>
                          )}
                          <View style={{ flex: 1 }}>
                            <Text style={s.userName}>{u.full_name}</Text>
                            <Text style={s.userEmail}>{u.email}</Text>
                          </View>
                        </TouchableOpacity>
                      ))
                    )}
                  </View>
                )}
              </View>

              {/* Selected user confirmation */}
              {selectedUser && (
                <View style={s.selectedUser}>
                  {selectedUser.profile_image ? (
                    <Image source={{ uri: selectedUser.profile_image }} style={s.selectedAvatar} />
                  ) : (
                    <View style={[s.selectedAvatar, s.userAvatarFallback]}>
                      <Text style={s.userAvatarInitial}>{selectedUser.full_name.charAt(0).toUpperCase()}</Text>
                    </View>
                  )}
                  <View>
                    <Text style={s.selectedName}>{selectedUser.full_name}</Text>
                    <Text style={s.selectedEmail}>{selectedUser.email}</Text>
                  </View>
                </View>
              )}

              {selectedUser && (
                <>
                  {/* Optional message */}
                  <Text style={s.label}>Mensaje (opcional)</Text>
                  <TextInput
                    style={[s.input, s.textarea]}
                    placeholder="¡Te voy a ganar!"
                    placeholderTextColor="#475569"
                    value={message}
                    onChangeText={setMessage}
                    multiline
                    numberOfLines={2}
                    maxLength={200}
                  />

                  {/* Topic selector */}
                  <Text style={s.label}>Modo de preguntas</Text>
                  <View style={s.topicsGrid}>
                    {TOPICS.map(t => (
                      <TouchableOpacity
                        key={t.value}
                        style={[s.topicBtn, topic === t.value && s.topicBtnActive]}
                        onPress={() => setTopic(t.value)}
                      >
                        <Text style={[s.topicBtnText, topic === t.value && s.topicBtnTextActive]}>
                          {t.label}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  <Text style={s.topicHint}>
                    {topic ? `Las 5 preguntas serán de ${topic}` : 'La rueda elegirá cualquier tema por ronda'}
                  </Text>
                </>
              )}

              <View style={s.formActions}>
                <TouchableOpacity
                  style={[s.btnPrimary, (!selectedUser || sendingChallenge) && s.btnDisabled]}
                  onPress={sendChallenge}
                  disabled={!selectedUser || sendingChallenge}
                >
                  <Text style={s.btnPrimaryText}>{sendingChallenge ? 'Enviando...' : '⚔️  Enviar Reto'}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={s.btnSecondary}
                  onPress={() => { setShowChallengeForm(false); setSelectedUser(null); setSearchQuery(''); setShowUserList(false); }}
                >
                  <Text style={s.btnSecondaryText}>Cancelar</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        </ScrollView>
      )}

      {/* ── PENDING TAB ── */}
      {activeTab === 'pending' && (
        <ScrollView contentContainerStyle={s.content}>
          <View style={s.listHeader}>
            <Text style={s.sectionTitle}>Retos Pendientes</Text>
            <TouchableOpacity onPress={fetchData} disabled={loadingData}>
              <Text style={s.refreshText}>{loadingData ? '...' : '↻ Actualizar'}</Text>
            </TouchableOpacity>
          </View>
          {loadingData && pendingDuels.length === 0 ? (
            <ActivityIndicator color="#6366F1" style={{ marginTop: 40 }} />
          ) : pendingDuels.length === 0 ? (
            <View style={s.empty}>
              <Text style={s.emptyEmoji}>⏳</Text>
              <Text style={s.emptyText}>No tienes retos pendientes</Text>
              <Text style={s.emptySub}>Cuando alguien te rete, aparecerá aquí</Text>
            </View>
          ) : (
            pendingDuels.map(duel => (
              <View key={duel.id} style={s.duelCard}>
                <View style={s.duelCardTop}>
                  {duel.challenger_image ? (
                    <Image source={{ uri: duel.challenger_image }} style={s.duelAvatar} />
                  ) : (
                    <View style={[s.duelAvatar, s.userAvatarFallback]}>
                      <Text style={s.userAvatarInitial}>{duel.challenger_name.charAt(0).toUpperCase()}</Text>
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={s.duelName}>{duel.challenger_name} te ha retado</Text>
                    <Text style={s.duelStatus}>{duel.status_message}</Text>
                    {duel.created_at && (
                      <Text style={s.duelDate}>
                        {new Date(duel.created_at).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </Text>
                    )}
                  </View>
                </View>

                {duel.challenger_message && (
                  <View style={s.messageBox}>
                    <Text style={s.messageText}>💬 "{duel.challenger_message}"</Text>
                  </View>
                )}

                <View style={s.topicChallenge}>
                  <Text style={s.topicChallengeText}>
                    {duel.duel_topic
                      ? `¡Te reto a ver qué tanto sabes de ${duel.duel_topic}!`
                      : '¡Te reto a ver qué tanto sabes de todo!'}
                  </Text>
                </View>

                <View style={s.duelActions}>
                  <TouchableOpacity style={s.btnPrimary} onPress={() => acceptDuel(duel)}>
                    <Text style={s.btnPrimaryText}>⚔️  Jugar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={s.btnSecondary}
                    onPress={() => Alert.alert('Rechazar duelo', '¿Estás seguro?', [
                      { text: 'Cancelar', style: 'cancel' },
                      { text: 'Rechazar', style: 'destructive', onPress: () => rejectDuel(duel.id) },
                    ])}
                  >
                    <Text style={s.btnSecondaryText}>Rechazar</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}

      {/* ── COMPLETED TAB ── */}
      {activeTab === 'completed' && (
        <ScrollView contentContainerStyle={s.content}>
          <View style={s.listHeader}>
            <Text style={s.sectionTitle}>Duelos Terminados</Text>
            <TouchableOpacity onPress={fetchData} disabled={loadingData}>
              <Text style={s.refreshText}>{loadingData ? '...' : '↻ Actualizar'}</Text>
            </TouchableOpacity>
          </View>
          {loadingData && completedDuels.length === 0 ? (
            <ActivityIndicator color="#6366F1" style={{ marginTop: 40 }} />
          ) : completedDuels.length === 0 ? (
            <View style={s.empty}>
              <Text style={s.emptyEmoji}>🏆</Text>
              <Text style={s.emptyText}>No hay duelos terminados</Text>
            </View>
          ) : (
            completedDuels.map(duel => {
              const isMe1 = duel.player1_id === user?.id;
              return (
                <View key={duel.id} style={s.duelCard}>
                  <View style={s.vsRow}>
                    {/* Player 1 */}
                    <View style={s.vsPlayer}>
                      {duel.player1_image ? (
                        <Image source={{ uri: duel.player1_image }} style={s.vsAvatar} />
                      ) : (
                        <View style={[s.vsAvatar, s.userAvatarFallback]}>
                          <Text style={s.userAvatarInitial}>{duel.player1_name.charAt(0).toUpperCase()}</Text>
                        </View>
                      )}
                      <Text style={s.vsName} numberOfLines={1}>{duel.player1_name}</Text>
                      <Text style={[s.vsScore, duel.winner_id === duel.player1_id && s.vsScoreWinner]}>
                        {duel.player1_score}
                      </Text>
                    </View>

                    <Text style={s.vsText}>VS</Text>

                    {/* Player 2 */}
                    <View style={s.vsPlayer}>
                      {duel.player2_image ? (
                        <Image source={{ uri: duel.player2_image }} style={s.vsAvatar} />
                      ) : (
                        <View style={[s.vsAvatar, s.userAvatarFallback]}>
                          <Text style={s.userAvatarInitial}>{duel.player2_name.charAt(0).toUpperCase()}</Text>
                        </View>
                      )}
                      <Text style={s.vsName} numberOfLines={1}>{duel.player2_name}</Text>
                      <Text style={[s.vsScore, duel.winner_id === duel.player2_id && s.vsScoreWinner]}>
                        {duel.player2_score}
                      </Text>
                    </View>
                  </View>

                  <Text style={s.resultText}>{duel.result_message}</Text>

                  {duel.challenger_message && (
                    <Text style={s.smallMessage}>💬 {duel.challenger_message}</Text>
                  )}
                  {duel.winner_message && (
                    <Text style={s.smallMessage}>🏆 {duel.winner_message}</Text>
                  )}
                </View>
              );
            })
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  tabBar: { flexDirection: 'row', backgroundColor: '#1E293B', borderBottomWidth: 1, borderBottomColor: '#334155' },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#6366F1' },
  tabText: { fontSize: 11, color: '#64748B', fontWeight: '500' },
  tabTextActive: { color: '#6366F1', fontWeight: '700' },
  content: { padding: 20, paddingBottom: 40 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 16 },
  listHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  refreshText: { color: '#6366F1', fontSize: 13 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 8 },
  emptyEmoji: { fontSize: 48 },
  emptyText: { fontSize: 16, color: '#94A3B8', fontWeight: '500' },
  emptySub: { fontSize: 13, color: '#475569', textAlign: 'center' },

  // Challenge form
  challengeBtn: { backgroundColor: '#1D4ED8', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  challengeBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  form: { backgroundColor: '#1E293B', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#334155', gap: 10 },
  label: { fontSize: 13, color: '#94A3B8', marginTop: 4 },
  input: { backgroundColor: '#0F172A', borderRadius: 10, padding: 12, color: '#F8FAFC', fontSize: 14, borderWidth: 1, borderColor: '#334155' },
  textarea: { height: 64, textAlignVertical: 'top' },
  dropdown: {
    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
    backgroundColor: '#1E293B', borderRadius: 10, borderWidth: 1, borderColor: '#334155',
    maxHeight: 200, overflow: 'hidden',
  },
  dropdownLoading: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14 },
  dropdownLoadingText: { color: '#94A3B8', fontSize: 13 },
  dropdownEmpty: { color: '#64748B', fontSize: 13, padding: 14, textAlign: 'center' },
  dropdownItem: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderBottomWidth: 1, borderBottomColor: '#334155' },
  dropdownItemSelected: { backgroundColor: '#334155' },
  userAvatar: { width: 36, height: 36, borderRadius: 18 },
  userAvatarFallback: { backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' },
  userAvatarInitial: { color: '#F8FAFC', fontSize: 14, fontWeight: 'bold' },
  userName: { fontSize: 13, fontWeight: '600', color: '#F8FAFC' },
  userEmail: { fontSize: 11, color: '#64748B' },
  selectedUser: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#0F172A', borderRadius: 10, padding: 12, borderWidth: 1, borderColor: '#334155' },
  selectedAvatar: { width: 44, height: 44, borderRadius: 22 },
  selectedName: { fontSize: 14, fontWeight: '600', color: '#F8FAFC' },
  selectedEmail: { fontSize: 12, color: '#64748B' },
  topicsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  topicBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: '#334155' },
  topicBtnActive: { backgroundColor: '#1D4ED8', borderColor: '#1D4ED8' },
  topicBtnText: { fontSize: 12, color: '#94A3B8' },
  topicBtnTextActive: { color: '#fff', fontWeight: '600' },
  topicHint: { fontSize: 11, color: '#475569', fontStyle: 'italic' },
  formActions: { flexDirection: 'row', gap: 10, marginTop: 4 },

  // Buttons
  btnPrimary: { flex: 1, backgroundColor: '#1D4ED8', borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  btnDisabled: { opacity: 0.4 },
  btnPrimaryText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  btnSecondary: { flex: 1, backgroundColor: '#1E293B', borderRadius: 10, paddingVertical: 13, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  btnSecondaryText: { color: '#94A3B8', fontSize: 14 },

  // Duel cards
  duelCard: { backgroundColor: '#1E293B', borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#334155', gap: 10 },
  duelCardTop: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  duelAvatar: { width: 48, height: 48, borderRadius: 24 },
  duelName: { fontSize: 14, fontWeight: '600', color: '#F8FAFC' },
  duelStatus: { fontSize: 12, color: '#64748B' },
  duelDate: { fontSize: 11, color: '#475569', marginTop: 2 },
  messageBox: { backgroundColor: '#0F172A', borderRadius: 8, padding: 10 },
  messageText: { fontSize: 13, color: '#94A3B8', fontStyle: 'italic' },
  topicChallenge: { backgroundColor: '#1C2A1E', borderRadius: 8, padding: 10 },
  topicChallengeText: { fontSize: 13, color: '#4ADE80', fontWeight: '500' },
  duelActions: { flexDirection: 'row', gap: 10 },

  // VS layout
  vsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around' },
  vsPlayer: { alignItems: 'center', flex: 1, gap: 4 },
  vsAvatar: { width: 52, height: 52, borderRadius: 26 },
  vsName: { fontSize: 12, color: '#F8FAFC', fontWeight: '500', textAlign: 'center', maxWidth: 100 },
  vsScore: { fontSize: 22, fontWeight: 'bold', color: '#94A3B8' },
  vsScoreWinner: { color: '#22C55E' },
  vsText: { fontSize: 24, fontWeight: 'black', color: '#475569', paddingHorizontal: 8 },
  resultText: { fontSize: 13, color: '#94A3B8', textAlign: 'center', fontWeight: '500' },
  smallMessage: { fontSize: 12, color: '#64748B', fontStyle: 'italic' },
});
