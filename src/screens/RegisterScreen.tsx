import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ScrollView,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useAuthStore } from '../store/authStore';
import { RootStackParamList } from '../navigation/types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Register'>;
};

export default function RegisterScreen({ navigation }: Props) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | null>(null);
  const { register, isLoading } = useAuthStore();

  const handleRegister = async () => {
    if (!username || !email || !password || !gender) {
      Alert.alert('Error', 'Por favor completa todos los campos');
      return;
    }
    try {
      await register({ username, email, password, gender });
    } catch {
      Alert.alert('Error', 'No se pudo crear la cuenta. Intenta con otro correo.');
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.inner}>
        <Text style={styles.title}>Crear cuenta</Text>
        <Text style={styles.subtitle}>Únete a Proyecto Residente</Text>

        <TextInput
          style={styles.input}
          placeholder="Nombre de usuario"
          placeholderTextColor="#9CA3AF"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TextInput
          style={styles.input}
          placeholder="Correo electrónico"
          placeholderTextColor="#9CA3AF"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          placeholderTextColor="#9CA3AF"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <Text style={styles.genderLabel}>Selecciona tu avatar</Text>
        <View style={styles.genderRow}>
          <TouchableOpacity
            style={[styles.genderButton, gender === 'male' && styles.genderSelected]}
            onPress={() => setGender('male')}
          >
            <Text style={styles.genderEmoji}>👨‍⚕️</Text>
            <Text style={[styles.genderText, gender === 'male' && styles.genderTextSelected]}>
              Masculino
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.genderButton, gender === 'female' && styles.genderSelected]}
            onPress={() => setGender('female')}
          >
            <Text style={styles.genderEmoji}>👩‍⚕️</Text>
            <Text style={[styles.genderText, gender === 'female' && styles.genderTextSelected]}>
              Femenino
            </Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleRegister}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Registrarse</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity onPress={() => navigation.navigate('Login')}>
          <Text style={styles.link}>¿Ya tienes cuenta? Inicia sesión</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  inner: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingVertical: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#F8FAFC',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginBottom: 32,
  },
  input: {
    width: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: '#F8FAFC',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  genderLabel: {
    color: '#94A3B8',
    fontSize: 14,
    alignSelf: 'flex-start',
    marginBottom: 8,
    marginTop: 4,
  },
  genderRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
    width: '100%',
  },
  genderButton: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#334155',
  },
  genderSelected: {
    borderColor: '#6366F1',
    backgroundColor: '#1E1B4B',
  },
  genderEmoji: {
    fontSize: 32,
    marginBottom: 4,
  },
  genderText: {
    color: '#94A3B8',
    fontSize: 13,
  },
  genderTextSelected: {
    color: '#818CF8',
    fontWeight: '600',
  },
  button: {
    width: '100%',
    backgroundColor: '#6366F1',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: 20,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  link: {
    color: '#818CF8',
    fontSize: 14,
  },
});
