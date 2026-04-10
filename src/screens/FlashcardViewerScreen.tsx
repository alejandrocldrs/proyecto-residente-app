import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator,
  SafeAreaView, Animated, PanResponder, Dimensions, Alert, Modal,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'FlashcardViewer'>;
  route: RouteProp<RootStackParamList, 'FlashcardViewer'>;
};

interface Card {
  id: string;
  question_text: string;
  answer_text: string;
  personal_notes?: string;
}

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function FlashcardViewerScreen({ navigation, route }: Props) {
  const { specialty, topic, deckName } = route.params;

  const [cards, setCards] = useState<Card[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isFlipped, setIsFlipped] = useState(false);
  const [deletingCard, setDeletingCard] = useState<string | null>(null);

  // Flip animation
  const flipAnim = useRef(new Animated.Value(0)).current;
  // Swipe animation
  const swipeAnim = useRef(new Animated.Value(0)).current;

  const flipToFront = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '90deg'] });
  const flipToBack = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['90deg', '0deg'] });

  useEffect(() => {
    api.get('/api/flashcards/by-deck', { params: { specialty, topic, quiz_title: deckName } })
      .then(r => setCards(r.data))
      .catch(() => Alert.alert('Error', 'No se pudieron cargar las tarjetas'))
      .finally(() => setLoading(false));
  }, [specialty, topic, deckName]);

  const flipCard = () => {
    if (isFlipped) {
      Animated.timing(flipAnim, { toValue: 0, duration: 200, useNativeDriver: true }).start(() => setIsFlipped(false));
    } else {
      setIsFlipped(true);
      Animated.timing(flipAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    }
  };

  const goToCard = (index: number) => {
    if (index < 0 || index >= cards.length) return;
    const direction = index > currentIndex ? -1 : 1;

    // Reset flip
    flipAnim.setValue(0);
    setIsFlipped(false);

    // Animate swipe out then in
    Animated.sequence([
      Animated.timing(swipeAnim, { toValue: direction * SCREEN_WIDTH, duration: 150, useNativeDriver: true }),
      Animated.timing(swipeAnim, { toValue: -direction * SCREEN_WIDTH, duration: 0, useNativeDriver: true }),
      Animated.timing(swipeAnim, { toValue: 0, duration: 150, useNativeDriver: true }),
    ]).start();

    setCurrentIndex(index);
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 10 && Math.abs(g.dy) < 60,
      onPanResponderRelease: (_, g) => {
        if (g.dx < -50) goToCard(currentIndex + 1);
        else if (g.dx > 50) goToCard(currentIndex - 1);
      },
    })
  ).current;

  const handleDeleteCard = async (cardId: string) => {
    try {
      await api.delete(`/api/flashcards/${cardId}`);
      const newCards = cards.filter(c => c.id !== cardId);
      setCards(newCards);
      setDeletingCard(null);
      if (newCards.length === 0) navigation.goBack();
      else if (currentIndex >= newCards.length) setCurrentIndex(newCards.length - 1);
    } catch {
      Alert.alert('Error', 'No se pudo eliminar la flashcard');
    }
  };

  if (loading) {
    return <View style={styles.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  if (cards.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <Text style={styles.emptyText}>No hay tarjetas en este paquete</Text>
        </View>
      </SafeAreaView>
    );
  }

  const card = cards[currentIndex];

  return (
    <SafeAreaView style={styles.container}>
      {/* Counter */}
      <Text style={styles.counter}>{currentIndex + 1} / {cards.length}</Text>
      <Text style={styles.deckLabel}>{deckName}</Text>

      {/* Card area */}
      <View style={styles.cardArea} {...panResponder.panHandlers}>
        {/* Stack layers */}
        {cards.length > 2 && <View style={[styles.stackCard, styles.stackFar]} />}
        {cards.length > 1 && <View style={[styles.stackCard, styles.stackNear]} />}

        {/* Animated card wrapper */}
        <Animated.View style={{ transform: [{ translateX: swipeAnim }], width: '100%' }}>
          <TouchableOpacity activeOpacity={1} onPress={flipCard}>
            {/* Front */}
            <Animated.View style={[styles.card, styles.cardFront, { transform: [{ rotateY: flipToFront }] }]}>
              <Text style={styles.cardHint}>Toca para ver la respuesta</Text>
              <Text style={styles.cardText}>{card.question_text}</Text>
            </Animated.View>
            {/* Back */}
            <Animated.View style={[styles.card, styles.cardBack, { transform: [{ rotateY: flipToBack }], position: 'absolute', top: 0, left: 0, right: 0 }]}>
              <Text style={styles.cardHint}>Respuesta</Text>
              <Text style={[styles.cardText, styles.cardTextBack]}>{card.answer_text}</Text>
              {!!card.personal_notes && (
                <Text style={styles.cardNotes}>{card.personal_notes}</Text>
              )}
            </Animated.View>
          </TouchableOpacity>
        </Animated.View>
      </View>

      {/* Hint */}
      <Text style={styles.swipeHint}>Desliza para navegar</Text>

      {/* Dot progress */}
      <View style={styles.dots}>
        {cards.map((_, i) => (
          <TouchableOpacity key={i} onPress={() => goToCard(i)}>
            <View style={[styles.dot, i === currentIndex && styles.dotActive]} />
          </TouchableOpacity>
        ))}
      </View>

      {/* Navigation & delete */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.navBtn, currentIndex === 0 && styles.navBtnDisabled]}
          onPress={() => goToCard(currentIndex - 1)}
          disabled={currentIndex === 0}
        >
          <Text style={styles.navBtnText}>‹</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.deleteCardBtn} onPress={() => setDeletingCard(card.id)}>
          <Text style={styles.deleteCardBtnText}>🗑 Eliminar</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navBtn, currentIndex === cards.length - 1 && styles.navBtnDisabled]}
          onPress={() => goToCard(currentIndex + 1)}
          disabled={currentIndex === cards.length - 1}
        >
          <Text style={styles.navBtnText}>›</Text>
        </TouchableOpacity>
      </View>

      {/* Delete confirmation */}
      <Modal visible={!!deletingCard} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>¿Eliminar flashcard?</Text>
            <Text style={styles.modalBody}>Esta acción no se puede deshacer.</Text>
            <TouchableOpacity style={styles.btnDanger} onPress={() => handleDeleteCard(deletingCard!)}>
              <Text style={styles.btnText}>Eliminar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.btnCancel} onPress={() => setDeletingCard(null)}>
              <Text style={styles.btnCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A', alignItems: 'center' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },
  counter: { color: '#64748B', fontSize: 13, marginTop: 8 },
  deckLabel: { color: '#94A3B8', fontSize: 14, fontWeight: '600', marginBottom: 16 },

  cardArea: { width: '88%', position: 'relative', marginBottom: 12 },
  stackCard: { position: 'absolute', left: 0, right: 0, borderRadius: 20, backgroundColor: '#1E293B' },
  stackFar: { bottom: -12, height: '100%', transform: [{ rotate: '2deg' }], opacity: 0.4 },
  stackNear: { bottom: -6, height: '100%', transform: [{ rotate: '1deg' }], opacity: 0.6 },

  card: {
    width: '100%', minHeight: 200, borderRadius: 20, padding: 28,
    justifyContent: 'center', alignItems: 'center', backfaceVisibility: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8,
    elevation: 8,
  },
  cardFront: { backgroundColor: '#1E293B', borderWidth: 1, borderColor: '#334155' },
  cardBack: { backgroundColor: '#312E81' },
  cardHint: { color: '#64748B', fontSize: 11, marginBottom: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  cardText: { fontSize: 18, color: '#F8FAFC', textAlign: 'center', lineHeight: 27, fontWeight: '500' },
  cardTextBack: { color: '#E0E7FF' },
  cardNotes: { marginTop: 16, fontSize: 13, color: '#818CF8', textAlign: 'center', fontStyle: 'italic' },

  swipeHint: { color: '#334155', fontSize: 12, marginBottom: 12 },

  dots: { flexDirection: 'row', gap: 6, marginBottom: 20 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#334155' },
  dotActive: { width: 20, backgroundColor: '#6366F1' },

  controls: { flexDirection: 'row', alignItems: 'center', gap: 20, paddingBottom: 20 },
  navBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#1E293B', justifyContent: 'center', alignItems: 'center' },
  navBtnDisabled: { opacity: 0.3 },
  navBtnText: { fontSize: 28, color: '#F8FAFC', lineHeight: 32 },
  deleteCardBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#334155' },
  deleteCardBtnText: { color: '#94A3B8', fontSize: 13 },
  emptyText: { color: '#64748B', fontSize: 15 },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalBox: { backgroundColor: '#1E293B', borderRadius: 20, padding: 24, width: '100%', borderWidth: 1, borderColor: '#334155', gap: 10 },
  modalTitle: { fontSize: 17, fontWeight: 'bold', color: '#F8FAFC' },
  modalBody: { fontSize: 14, color: '#94A3B8' },
  btnDanger: { backgroundColor: '#DC2626', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  btnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnCancel: { backgroundColor: '#0F172A', borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: '#334155' },
  btnCancelText: { color: '#94A3B8', fontSize: 15 },
});
