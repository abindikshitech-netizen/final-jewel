import React, { useEffect, useState } from "react";
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
import Slider from "@react-native-community/slider";

// ⚠️ For real mobile device, replace localhost with your PC IP
// Example: http://192.168.1.5:8000
const BACKEND_URL = "http://localhost:8000";

const NECKLACES = [
  { name: "necklace1", img: `${BACKEND_URL}/jewelry/necklace1.png` },
  { name: "necklace2", img: `${BACKEND_URL}/jewelry/necklace2.png` },
  { name: "necklace3", img: `${BACKEND_URL}/jewelry/necklace3.png` },
  { name: "necklace4", img: `${BACKEND_URL}/jewelry/necklace4.png` },
  { name: "necklace5", img: `${BACKEND_URL}/jewelry/necklace5.png` },
];

const EARRINGS = [
  { name: "earring1", img: `${BACKEND_URL}/jewelry/earring1.png` },
  { name: "earring2", img: `${BACKEND_URL}/jewelry/earring2.png` },
  { name: "earring3", img: `${BACKEND_URL}/jewelry/earring3.png` },
  { name: "earring4", img: `${BACKEND_URL}/jewelry/earring4.png` },
  { name: "earring5", img: `${BACKEND_URL}/jewelry/earring5.png` },
];

const RINGS = [
  { name: "ring1", img: `${BACKEND_URL}/jewelry/ring1.png` },
  { name: "ring2", img: `${BACKEND_URL}/jewelry/ring2.png` },
  { name: "ring3", img: `${BACKEND_URL}/jewelry/ring3.png` },
  { name: "ring4", img: `${BACKEND_URL}/jewelry/ring4.png` },
  { name: "ring5", img: `${BACKEND_URL}/jewelry/ring5.png` },
];

const BRACELETS = [
  { name: "bracelet1", img: `${BACKEND_URL}/jewelry/bracelet1.png` },
  { name: "bracelet2", img: `${BACKEND_URL}/jewelry/bracelet2.png` },
  { name: "bracelet3", img: `${BACKEND_URL}/jewelry/bracelet3.png` },
  { name: "bracelet4", img: `${BACKEND_URL}/jewelry/bracelet4.png` },
];

type JewelleryType = "necklace" | "earring" | "ring" | "bracelet";

export default function App() {
  const [image, setImage] = useState<string | null>(null);
  const [output, setOutput] = useState<string | null>(null);
  const [type, setType] = useState<JewelleryType>("necklace");
  const [item, setItem] = useState("necklace1");
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);

  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    if (type === "necklace") {
      setItem("necklace1");
    } else if (type === "earring") {
      setItem("earring1");
    } else if (type === "ring") {
      setItem("ring1");
    } else if (type === "bracelet") {
      setItem("bracelet1");
    }

    resetControls();
    setOutput(null);
  }, [type]);

  const resetControls = () => {
    setScale(1);
    setOffsetX(0);
    setOffsetY(0);
    setRotation(0);
  };

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
      if (!image) {
        return Alert.alert("Select image");
      }

      setLoading(true);

      const base64 = await RNFS.readFile(image, "base64");

      const res = await fetch(`${BACKEND_URL}/tryon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: base64,
          type,
          item,
          scale,
          offset_x: offsetX,
          offset_y: offsetY,
          rotation,
        }),
      });

      const data = await res.json();
      setLoading(false);

      if (data.output) {
        setOutput(`${BACKEND_URL}/${data.output}?t=${Date.now()}`);
      } else {
        Alert.alert("Error", data.error || "Error processing image");
      }
    } catch (error) {
      setLoading(false);
      Alert.alert("Server error");
    }
  };

  const renderItems = (data: { name: string; img: string }[]) => (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      {data.map((i) => (
        <TouchableOpacity
          key={i.name}
          onPress={() => {
            setItem(i.name);
            setOutput(null);
          }}
          style={[styles.itemCard, item === i.name && styles.activeItem]}
        >
          <Image source={{ uri: i.img }} style={styles.itemImage} />
        </TouchableOpacity>
      ))}
    </ScrollView>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Jewellery Try-On</Text>

      <TouchableOpacity style={styles.uploadBtn} onPress={pickImage}>
        <Text style={styles.uploadText}>Select Image</Text>
      </TouchableOpacity>

      <View style={styles.tabRow}>
        <TouchableOpacity onPress={() => setType("necklace")} style={styles.tabBtn}>
          <Text style={type === "necklace" ? styles.activeTab : styles.tab}>
            Necklace
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setType("earring")} style={styles.tabBtn}>
          <Text style={type === "earring" ? styles.activeTab : styles.tab}>
            Earrings
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setType("ring")} style={styles.tabBtn}>
          <Text style={type === "ring" ? styles.activeTab : styles.tab}>
            Ring
          </Text>
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setType("bracelet")} style={styles.tabBtn}>
          <Text style={type === "bracelet" ? styles.activeTab : styles.tab}>
            Bracelet
          </Text>
        </TouchableOpacity>
      </View>

      {type === "necklace" && renderItems(NECKLACES)}
      {type === "earring" && renderItems(EARRINGS)}
      {type === "ring" && renderItems(RINGS)}
      {type === "bracelet" && renderItems(BRACELETS)}

      <View style={styles.adjustBox}>
        <Text style={styles.adjustTitle}>
          {type.charAt(0).toUpperCase() + type.slice(1)} Adjustment
        </Text>

        <Text style={styles.sliderLabel}>Scale: {scale.toFixed(2)}</Text>
        <Slider
          minimumValue={0.4}
          maximumValue={2.2}
          value={scale}
          onValueChange={(v) => {
            setScale(v);
            setOutput(null);
          }}
        />

        <Text style={styles.sliderLabel}>Move X: {Math.round(offsetX)}</Text>
        <Slider
          minimumValue={-160}
          maximumValue={160}
          value={offsetX}
          onValueChange={(v) => {
            setOffsetX(v);
            setOutput(null);
          }}
        />

        <Text style={styles.sliderLabel}>Move Y: {Math.round(offsetY)}</Text>
        <Slider
          minimumValue={-160}
          maximumValue={160}
          value={offsetY}
          onValueChange={(v) => {
            setOffsetY(v);
            setOutput(null);
          }}
        />

        <Text style={styles.sliderLabel}>Rotation: {Math.round(rotation)}°</Text>
        <Slider
          minimumValue={-180}
          maximumValue={180}
          value={rotation}
          onValueChange={(v) => {
            setRotation(v);
            setOutput(null);
          }}
        />

        <TouchableOpacity
          style={styles.resetBtn}
          onPress={() => {
            resetControls();
            setOutput(null);
          }}
        >
          <Text style={styles.resetText}>Reset Controls</Text>
        </TouchableOpacity>
      </View>

      {image && (
        <>
          <Text style={styles.sectionTitle}>Selected Image</Text>
          <Image source={{ uri: image }} style={styles.image} />
        </>
      )}

      <TouchableOpacity style={styles.tryBtn} onPress={tryOn} disabled={loading}>
        <Text style={styles.tryText}>{loading ? "Processing..." : "Try On"}</Text>
      </TouchableOpacity>

      {loading && <ActivityIndicator size="large" color="#b8860b" style={styles.loader} />}

      {output && (
        <>
          <Text style={styles.sectionTitle}>Output</Text>
          <TouchableOpacity onPress={() => setVisible(true)}>
            <Image source={{ uri: output }} style={styles.image} />
          </TouchableOpacity>
        </>
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
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },

  content: {
    padding: 16,
    paddingBottom: 30,
  },

  title: {
    fontSize: 24,
    textAlign: "center",
    color: "#b8860b",
    fontWeight: "bold",
    marginBottom: 10,
  },

  uploadBtn: {
    backgroundColor: "#ddd",
    padding: 12,
    marginVertical: 10,
    borderRadius: 10,
  },

  uploadText: {
    textAlign: "center",
    fontWeight: "600",
  },

  tabRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginVertical: 10,
    flexWrap: "wrap",
  },

  tabBtn: {
    paddingVertical: 8,
    paddingHorizontal: 10,
  },

  tab: {
    color: "#888",
    fontSize: 15,
  },

  activeTab: {
    color: "#b8860b",
    fontWeight: "bold",
    fontSize: 15,
  },

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

  adjustBox: {
    backgroundColor: "#fff8e6",
    padding: 12,
    borderRadius: 12,
    marginTop: 10,
    borderWidth: 1,
    borderColor: "#e7c766",
  },

  adjustTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#9e7a02",
    marginBottom: 6,
  },

  sliderLabel: {
    color: "#333",
    fontWeight: "600",
    marginTop: 8,
  },

  resetBtn: {
    backgroundColor: "#eee",
    padding: 10,
    borderRadius: 8,
    marginTop: 8,
  },

  resetText: {
    textAlign: "center",
    fontWeight: "bold",
    color: "#333",
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#333",
    marginTop: 12,
    marginBottom: 6,
  },

  image: {
    width: "100%",
    height: 350,
    resizeMode: "contain",
    marginVertical: 10,
    backgroundColor: "#f8f8f8",
    borderRadius: 10,
  },

  tryBtn: {
    backgroundColor: "#9e7a02",
    padding: 15,
    borderRadius: 10,
    marginTop: 10,
  },

  tryText: {
    textAlign: "center",
    color: "#fff",
    fontWeight: "bold",
  },

  loader: {
    marginTop: 15,
  },
});