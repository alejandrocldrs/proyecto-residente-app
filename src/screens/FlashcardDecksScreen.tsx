import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Modal, TextInput, Alert,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'FlashcardDecks'>;
  route: RouteProp<RootStackParamList, 'FlashcardDecks'>;
};

interface DeckInfo { count: number }

export default function FlashcardDecksScreen({ navigation, route }: Props) {
  const { specialty, topic } = route.params;
  const [decks, setDecks] = useState<Record<string, DeckInfo>>({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deletingDeck, setDeletingDeck] = useState<string | null>(null);

  const fetchDecks = useCallback(() => {
    setLoading(true);
    api.get('/api/flashcards/grouped')
      .then(r => setDecks(r.data[specialty]?.topics?.[topic]?.quizzes ?? {}))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [specialty, topic]);

  useEffect(() => { fetchDecks(); }, [fetchDecks]);

  const handleDeleteDeck = async (deckName: string) => {
    try {
      await api.delete('/api/flashcards/deck', { params: { topic, quiz_title: deckName } });
      setDeletingDeck(null);
      fetchDecks();
    } catch {
      Alert.alert('Error', 'No se pudo eliminar el paquete');
    }
  };

  const deckNames = Object.keys(decks);

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>{topic}</Text>
        <Text style={styles.subtitle}>{specialty}</Text>

        {/* Add card button */}
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowCreateModal(true)}>
          <Text style={styles.addBtnText}>＋  Agregar flashcard</Text>
        </TouchableOpacity>

        {deckNames.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>🃏</Text>
            <Text style={styles.emptyText}>No hay paquetes aún</Text>
            <Text style={styles.emptySub}>Guarda preguntas desde un cuestionario</Text>
          </View>
        ) : (
          deckNames.map((deckName) => {
            const count = decks[deckName]?.count ?? 0;
            return (
              <View key={deckName} style={styles.card}>
                <TouchableOpacity
                  style={styles.cardMain}
                  onPress={() => navigation.navigate('FlashcardViewer', { specialty, topic, deckName })}
                  activeOpacity={0.7}
                >
                  <Text style={styles.deckIcon}>🃏</Text>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardTitle}>Flash Cards + {deckName}</Text>
                    <Text style={styles.cardCount}>{count} {count === 1 ? 'tarjeta' : 'tarjetas'}</Text>
                  </View>
                  <Text style={styles.chevron}>›</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.deleteBtn}
                  onPress={() => setDeletingDeck(deckName)}
                >
                  <Text style={styles.deleteBtnText}>🗑</Text>
                </TouchableOpacity>
              </View>
            );
          })
        )}
      </ScrollView>

      {/* Delete confirmation modal */}
      <Modal visible={!!deletingDeck} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>¿Eliminar paquete completo?</Text>
            <Text style={styles.modalBody}>
              Se eliminarán todas las flashcards de "{deletingDeck}". Esta acción no se puede deshacer.
            </Text>
            <TouchableOpacity style={styles.btnDanger} onPress={() => handleDeleteDeck(deletingDeck!)}>
              <Text style={styles.btnDangerText}>Eliminar todo</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnCancel} onPress={() => setDeletingDeck(null)}>
              <Text style={styles.btnCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Create flashcard modal */}
      {showCreateModal && (
        <CreateFlashcardModal
          specialty={specialty}
          topic={topic}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => { setShowCreateModal(false); fetchDecks(); }}
        />
      )}
    </SafeAreaView>
  );
}

// ── Create Flashcard Modal ────────────────────────────────────────────────────
function CreateFlashcardModal({
  specialty, topic, deckName: defaultDeck = '',
  onClose, onSuccess,
}: {
  specialty: string; topic: string; deckName?: string;
  onClose: () => void; onSuccess: () => void;
}) {
  const [quizTitle, setQuizTitle] = useState(defaultDeck);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!quizTitle || !question || !answer) {
      Alert.alert('Campos requeridos', 'Completa el paquete, pregunta y respuesta');
      return;
    }
    setSaving(true);
    try {
      await api.post('/api/flashcards/manual', {
        specialty, topic, quiz_title: quizTitle,
        question_text: question, answer_text: answer, personal_notes: notes,
      });
      onSuccess();
    } catch {
      Alert.alert('Error', 'No se pudo guardar la flashcard');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible transparent animationType="slide">
      <View style={styles.modalOverlay}>
        <View style={[styles.modalBox, { maxHeight: '85%' }]}>
          <ScrollView showsVerticalScrollIndicator={false}>
            <Text style={styles.modalTitle}>Nueva Flashcard</Text>
            <Text style={styles.fieldLabel}>Paquete *</Text>
            <TextInput style={styles.input} value={quizTitle} onChangeText={setQuizTitle} placeholder="Ej: Hipotiroidismo" placeholderTextColor="#475569" />
            <Text style={styles.fieldLabel}>Pregunta *</Text>
            <TextInput style={[styles.input, styles.textarea]} value={question} onChangeText={setQuestion} placeholder="Escribe la pregunta..." placeholderTextColor="#475569" multiline numberOfLines={3} />
            <Text style={styles.fieldLabel}>Respuesta *</Text>
            <TextInput style={[styles.input, styles.textarea]} value={answer} onChangeText={setAnswer} placeholder="Escribe la respuesta..." placeholderTextColor="#475569" multiline numberOfLines={3} />
            <Text style={styles.fieldLabel}>Notas personales</Text>
            <TextInput style={[styles.input, styles.textarea]} value={notes} onChangeText={setNotes} placeholder="Opcional..." placeholderTextColor="#475569" multiline numberOfLines={2} />
            <TouchableOpacity style={styles.btnPrimary} onPress={handleSave} disabled={saving}>
              <Text style={styles.btnPrimaryText}>{saving ? 'Guardando...' : 'Guardar'}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnCancel} onPress={onClose}>
              <Text style={styles.btnCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 2 },
  subtitle: { fontSize: 13, color: '#64748B', marginBottom: 20 },
  addBtn: { borderWidth: 1.5, borderColor: '#334155', borderStyle: 'dashed', borderRadius: 12, padding: 14, alignItems: 'center', marginBottom: 20 },
  addBtnText: { color: '#64748B', fontSize: 14 },
  empty: { alignItems: 'center', paddingTop: 40, gap: 8 },
  emptyEmoji: { fontSize: 40 },
  emptyText: { color: '#94A3B8', fontSize: 15, fontWeight: '500' },
  emptySub: { color: '#475569', fontSize: 13, textAlign: 'center' },
  card: { backgroundColor: '#1E293B', borderRadius: 14, marginBottom: 10, borderWidth: 1, borderColor: '#334155', overflow: 'hidden' },
  cardMain: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  deckIcon: { fontSize: 28, marginRight: 14 },
  cardContent: { flex: 1 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: '#E2E8F0', marginBottom: 3 },
  cardCount: { fontSize: 12, color: '#64748B' },
  chevron: { fontSize: 22, color: '#475569' },
  deleteBtn: { borderTopWidth: 1, borderTopColor: '#334155', padding: 10, alignItems: 'center' },
  deleteBtnText: { fontSize: 16 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalBox: { backgroundColor: '#1E293B', borderRadius: 20, padding: 24, width: '100%', borderWidth: 1, borderColor: '#334155' },
  modalTitle: { fontSize: 17, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 12 },
  modalBody: { fontSize: 14, color: '#94A3B8', lineHeight: 21, marginBottom: 16 },
  fieldLabel: { color: '#94A3B8', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: { backgroundColor: '#0F172A', borderRadius: 10, padding: 12, color: '#F8FAFC', fontSize: 14, borderWidth: 1, borderColor: '#334155' },
  textarea: { height: 80, textAlignVertical: 'top' },
  btnPrimary: { backgroundColor: '#6366F1', borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 16 },
  btnPrimaryText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnDanger: { backgroundColor: '#DC2626', borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginBottom: 10 },
  btnDangerText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnCancel: { backgroundColor: '#0F172A', borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#334155', marginTop: 8 },
  btnCancelText: { color: '#94A3B8', fontSize: 15 },
});
