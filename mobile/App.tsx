import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { SafeAreaView, StyleSheet, View } from "react-native";

import TabBar, { TabKey } from "./src/components/TabBar";
import { AuthProvider, useAuth } from "./src/hooks/useAuth";
import HomeScreen from "./src/screens/HomeScreen";
import LoginScreen from "./src/screens/LoginScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import UploadScreen from "./src/screens/UploadScreen";

function Main() {
  const { user } = useAuth();
  const [tab, setTab] = useState<TabKey>("home");

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <View style={styles.root}>
      <View style={styles.content}>
        {tab === "home" && <HomeScreen />}
        {tab === "upload" && <UploadScreen />}
        {tab === "profile" && <ProfileScreen />}
      </View>
      <TabBar active={tab} onChange={setTab} />
    </View>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <SafeAreaView style={styles.root}>
        <Main />
        <StatusBar style="auto" />
      </SafeAreaView>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#f7f8fa" },
  content: { flex: 1 },
});
