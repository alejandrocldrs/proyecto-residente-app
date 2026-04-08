import React from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, SafeAreaView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { getSubmodules } from '../data/specialtyStructure';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Submodules'>;
  route: RouteProp<RootStackParamList, 'Submodules'>;
};

export default function SubmodulesScreen({ navigation, route }: Props) {
  const { specialty } = route.params;
  const submodules = getSubmodules(specialty);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>{specialty}</Text>
        <Text style={styles.subtitle}>Selecciona un submódulo</Text>

        {submodules.map((submodule, index) => (
          <TouchableOpacity
            key={submodule}
            style={styles.item}
            onPress={() => navigation.navigate('Topics', { specialty, submodule })}
            activeOpacity={0.7}
          >
            <View style={styles.dot} />
            <Text style={styles.itemText}>{submodule}</Text>
            <Text style={styles.arrow}>›</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#64748B', marginBottom: 24 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#6366F1',
    marginRight: 16,
  },
  itemText: { flex: 1, fontSize: 16, color: '#E2E8F0', fontWeight: '500' },
  arrow: { fontSize: 22, color: '#475569' },
});
