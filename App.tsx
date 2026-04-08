import { StatusBar } from 'expo-status-bar';
import { enableScreens } from 'react-native-screens';
import AppNavigator from './src/navigation/AppNavigator';

enableScreens();

export default function App() {
  return (
    <>
      <StatusBar style="light" />
      <AppNavigator />
    </>
  );
}
