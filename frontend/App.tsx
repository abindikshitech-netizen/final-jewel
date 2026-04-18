import React, { useState } from "react";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { launchImageLibrary } from "react-native-image-picker";
import RNFS from "react-native-fs";
import ImageViewing from "react-native-image-viewing";

const BACKEND_URL = "http://localhost:8000";

const NECKLACES = [
  { name: "necklace1", img: `${BACKEND_URL}/jewelry/necklace1.png` },
  { name: "necklace2", img: `${BACKEND_URL}/jewelry/necklace2.png` },
  { name: "necklace3", img: `${BACKEND_URL}/jewelry/necklace3.png` },
  { name: "necklace4", img: `${BACKEND_URL}/jewelry/necklace4.png` },
  { name: "necklace5", img: `${BACKEND_URL}/jewelry/necklace5.png` },
  { name: "necklace6", img: `${BACKEND_URL}/jewelry/necklace6.png` },
];

const EARRINGS = [
  { name: "earring1", img: `${BACKEND_URL}/jewelry/earring1.png` },
  { name: "earring2", img: `${BACKEND_URL}/jewelry/earring2.png` },
  { name: "earring3", img: `${BACKEND_URL}/jewelry/earring3.png` },
  { name: "earring4", img: `${BACKEND_URL}/jewelry/earring4.png` },
];

export default function App() {
  const [image, setImage] = useState<string | null>(null);
  const [output, setOutput] = useState<string | null>(null);
  const [type, setType] = useState("necklace");
  const [item, setItem] = useState("necklace1");
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);

  const pickImage = () => {
    launchImageLibrary({ mediaType: "photo" }, (res) => {
      if (res.assets && res.assets.length > 0) {
        setImage(res.assets[0].uri || null);
        setOutput(null);
      }
    });
  };

  const tryOn = async () => {
    try {
      if (!image) return Alert.alert("Select image");

      setLoading(true);

      const base64 = await RNFS.readFile(image, "base64");

      const res = await fetch(`${BACKEND_URL}/tryon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64, type, item }),
      });

      const data = await res.json();
      setLoading(false);

      if (data.output) {
        setOutput(`${BACKEND_URL}/${data.output}?t=${Date.now()}`);
      } else {
        Alert.alert("Error processing image");
      }
    } catch {
      setLoading(false);
      Alert.alert("Server error");
    }
  };

  const renderItems = (data: any[]) => (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      {data.map((i) => (
        <TouchableOpacity
          key={i.name}
          onPress={() => setItem(i.name)}
          style={[
            styles.itemCard,
            item === i.name && styles.activeItem,
          ]}
        >
          <Image source={{ uri: i.img }} style={styles.itemImage} />
        </TouchableOpacity>
      ))}
    </ScrollView>
  );

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Jewellery Try-On</Text>

      <TouchableOpacity style={styles.uploadBtn} onPress={pickImage}>
        <Text>Select Image</Text>
      </TouchableOpacity>

      <View style={styles.tabRow}>
        <TouchableOpacity onPress={() => setType("necklace")}>
          <Text style={type === "necklace" ? styles.activeTab : styles.tab}>
            Necklace
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setType("earring")}>
          <Text style={type === "earring" ? styles.activeTab : styles.tab}>
            Earrings
          </Text>
        </TouchableOpacity>
      </View>

      {type === "necklace" && renderItems(NECKLACES)}
      {type === "earring" && renderItems(EARRINGS)}

      {image && <Image source={{ uri: image }} style={styles.image} />}

      <TouchableOpacity style={styles.tryBtn} onPress={tryOn}>
        <Text style={styles.tryText}>Try On</Text>
      </TouchableOpacity>

      {loading && (
        <ActivityIndicator size="large" color="#b8860b" />
      )}

      {output && (
        <TouchableOpacity onPress={() => setVisible(true)}>
          <Image source={{ uri: output }} style={styles.image} />
        </TouchableOpacity>
      )}

      <ImageViewing
        images={output ? [{ uri: output }] : []}
        imageIndex={0}
        visible={visible}
        onRequestClose={() => setVisible(false)}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff", padding: 16 },

  title: {
    fontSize: 24,
    textAlign: "center",
    color: "#b8860b",
    fontWeight: "bold",
  },

  uploadBtn: {
    backgroundColor: "#ddd",
    padding: 12,
    marginVertical: 10,
    borderRadius: 10,
  },

  tabRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginVertical: 10,
  },

  tab: { color: "#888" },
  activeTab: { color: "#b8860b", fontWeight: "bold" },

  itemCard: {
    margin: 8,
    padding: 8,
    borderRadius: 10,
    backgroundColor: "#f5f5f5",
  },

  activeItem: {
    borderColor: "#b8860b",
    borderWidth: 2,
    shadowColor: "#b8860b",
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 5,
  },

  itemImage: {
    width: 70,
    height: 70,
    resizeMode: "contain",
  },

  image: {
    width: "100%",
    height: 350,
    resizeMode: "contain",
    marginVertical: 10,
  },

  tryBtn: {
    backgroundColor: "#b8860b",
    padding: 15,
    borderRadius: 10,
  },

  tryText: {
    textAlign: "center",
    color: "#fff",
    fontWeight: "bold",
  },
});