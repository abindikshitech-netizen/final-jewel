/**
 * @format
 */

import { AppRegistry } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

// 🔥 REGISTER APP (MUST MATCH app.json name)
AppRegistry.registerComponent(appName, () => App);