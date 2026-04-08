import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { useAuthStore } from '../store/authStore';

interface FeatureCard {
  title: string;
  description: string;
  emoji: string;
  screen: string;
  color: string;
}

const features: FeatureCard[] = [
  { title: 'Cuestionarios', description: 'Practica por tema y especialidad', emoji: '📚', screen: 'Topics', color: '#4F46E5' },
  { title: 'Flashcards', description: 'Repasa conceptos clave', emoji: '🃏', screen: 'Flashcards', color: '#7C3AED' },
  { title: 'Simulacros', description: 'Exámenes tipo ENARM', emoji: '📝', screen: 'Simulacros', color: '#0891B2' },
  { title: 'Duelos', description: 'Compite contra otros', emoji: '⚔️', screen: 'Duels', color: '#DC2626' },
  { title: 'ImagenDX', description: 'Diagnóstico por imagen', emoji: '🩻', screen: 'ImagenDX', color: '#059669' },
  { title: 'Planificador', description: 'Organiza tu estudio', emoji: '📅', screen: 'Planner', color: '#D97706' },
  { title: 'Perlas diarias', description: 'Aprende algo nuevo cada día', emoji: '💎', screen: 'Perlas', color: '#DB2777' },
  { title: 'Presentaciones', description: 'Material de apoyo', emoji: '🎯', screen: 'Presentaciones', color: '#7C3AED' },
  { title: 'Ranking', description: 'Tu posición entre todos', emoji: '🏆', screen: 'Leaderboard', color: '#CA8A04' },
  { title: 'Camino del Médico', description: 'Tu progresión y logros', emoji: '🩺', screen: 'CaminoDelMedico', color: '#4F46E5' },
];

export default function HomeScreen({ navigation }: any) {
  const { user, logout } = useAuthStore();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>¡Hola, {user?.username ?? 'Residente'}! 👋</Text>
            <Text style={styles.subgreeting}>¿Listo para estudiar hoy?</Text>
          </View>
          <TouchableOpacity onPress={() => navigation.navigate('Profile')} style={styles.avatarButton}>
            <Text style={styles.avatarEmoji}>
              {user?.gender === 'female' ? '👩‍⚕️' : '👨‍⚕️'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Points / Rank bar */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{user?.points ?? 0}</Text>
            <Text style={styles.statLabel}>Puntos</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{user?.rank ?? 'Estudiante'}</Text>
            <Text style={styles.statLabel}>Rango</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{user?.subscription_type ?? 'Free'}</Text>
            <Text style={styles.statLabel}>Plan</Text>
          </View>
        </View>

        {/* Feature grid */}
        <Text style={styles.sectionTitle}>¿Qué quieres estudiar?</Text>
        <View style={styles.grid}>
          {features.map((feature) => (
            <TouchableOpacity
              key={feature.screen}
              style={[styles.card, { borderLeftColor: feature.color }]}
              onPress={() => navigation.navigate(feature.screen)}
              activeOpacity={0.7}
            >
              <Text style={styles.cardEmoji}>{feature.emoji}</Text>
              <Text style={styles.cardTitle}>{feature.title}</Text>
              <Text style={styles.cardDescription}>{feature.description}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={logout}>
          <Text style={styles.logoutText}>Cerrar sesión</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
  },
  greeting: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#F8FAFC',
  },
  subgreeting: {
    fontSize: 13,
    color: '#94A3B8',
    marginTop: 2,
  },
  avatarButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarEmoji: {
    fontSize: 26,
  },
  statsCard: {
    flexDirection: 'row',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    marginHorizontal: 20,
    marginTop: 12,
    marginBottom: 24,
    paddingVertical: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#F8FAFC',
  },
  statLabel: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    backgroundColor: '#334155',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#F8FAFC',
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
    gap: 8,
  },
  card: {
    width: '47%',
    backgroundColor: '#1E293B',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 4,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardEmoji: {
    fontSize: 28,
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F8FAFC',
    marginBottom: 4,
  },
  cardDescription: {
    fontSize: 11,
    color: '#64748B',
  },
  logoutButton: {
    margin: 20,
    paddingVertical: 12,
    alignItems: 'center',
  },
  logoutText: {
    color: '#64748B',
    fontSize: 14,
  },
});
