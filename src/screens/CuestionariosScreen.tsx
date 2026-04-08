import React from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, SafeAreaView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { baseSpecialties, hasSubmodules, specialtyEmoji } from '../data/specialtyStructure';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Cuestionarios'>;
};

export default function CuestionariosScreen({ navigation }: Props) {
  const handleSpecialtyPress = (specialty: string) => {
    if (hasSubmodules(specialty)) {
      navigation.navigate('Submodules', { specialty });
    } else {
      navigation.navigate('Topics', { specialty });
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Cuestionarios</Text>
        <Text style={styles.subtitle}>Selecciona una especialidad</Text>

        {baseSpecialties.map((specialty) => (
          <TouchableOpacity
            key={specialty}
            style={styles.card}
            onPress={() => handleSpecialtyPress(specialty)}
            activeOpacity={0.7}
          >
            <Text style={styles.cardEmoji}>{specialtyEmoji[specialty]}</Text>
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>{specialty}</Text>
              <Text style={styles.cardSub}>
                {hasSubmodules(specialty) ? 'Ver submódulos →' : 'Ver temas →'}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#64748B', marginBottom: 24 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E293B',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardEmoji: { fontSize: 36, marginRight: 16 },
  cardContent: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#F8FAFC', marginBottom: 4 },
  cardSub: { fontSize: 13, color: '#64748B' },
});
