import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { SafeAreaView, StyleSheet, View } from "react-native";

import TabBar, { TabKey } from "./src/components/TabBar";
import { AuthProvider, useAuth } from "./src/hooks/useAuth";
import ActivityScreen from "./src/screens/ActivityScreen";
import HomeScreen from "./src/screens/HomeScreen";
import LoginScreen from "./src/screens/LoginScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import ScoreScreen from "./src/screens/ScoreScreen";
import UploadScreen from "./src/screens/UploadScreen";

function Main() {
  const { user } = useAuth();
  const [tab, setTab] = useState<TabKey>("home");
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);

  if (!user) {
    return <LoginScreen />;
  }

  // 動画選択中はスコア画面をタブより前面に表示
  if (selectedVideoId) {
    return <ScoreScreen videoId={selectedVideoId} onBack={() => setSelectedVideoId(null)} />;
  }

  return (
    <View style={styles.root}>
      <View style={styles.content}>
        {tab === "home" && <HomeScreen onSelectVideo={setSelectedVideoId} />}
        {tab === "upload" && <UploadScreen />}
        {tab === "activity" && <ActivityScreen />}
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
