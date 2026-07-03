/**
 * 5 軸レーダーチャート（依存: react-native-svg）。
 *
 * スコアは 0〜100 を想定。各軸のラベルと値を受け取り、
 * 正多角形グリッド + スコアポリゴンを描画する。
 */

import React from "react";
import { StyleSheet, View } from "react-native";
import Svg, { Circle, Line, Polygon, Text as SvgText } from "react-native-svg";

import { colors } from "../utils/theme";

export interface RadarAxis {
  label: string;
  value: number; // 0〜100
}

interface Props {
  axes: RadarAxis[];
  size?: number;
  maxValue?: number;
}

function polarPoint(cx: number, cy: number, radius: number, angleRad: number): [number, number] {
  return [cx + radius * Math.cos(angleRad), cy + radius * Math.sin(angleRad)];
}

export default function RadarChart({ axes, size = 260, maxValue = 100 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const padding = 36;
  const radius = size / 2 - padding;
  const count = axes.length;

  // 頂点を上（-90°）から時計回りに配置
  const angleFor = (i: number): number => (Math.PI * 2 * i) / count - Math.PI / 2;

  // グリッド（同心多角形）のレベル
  const levels = [0.25, 0.5, 0.75, 1];

  const gridPolygons = levels.map((level) =>
    axes
      .map((_, i) => {
        const [x, y] = polarPoint(cx, cy, radius * level, angleFor(i));
        return `${x},${y}`;
      })
      .join(" ")
  );

  const scorePoints = axes
    .map((axis, i) => {
      const ratio = Math.max(0, Math.min(1, axis.value / maxValue));
      const [x, y] = polarPoint(cx, cy, radius * ratio, angleFor(i));
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <View style={styles.container} testID="radar-chart">
      <Svg width={size} height={size}>
        {/* グリッド多角形 */}
        {gridPolygons.map((pts, i) => (
          <Polygon
            key={`grid-${i}`}
            points={pts}
            fill="none"
            stroke={colors.border}
            strokeWidth={1}
          />
        ))}

        {/* 軸線 + ラベル */}
        {axes.map((axis, i) => {
          const [x, y] = polarPoint(cx, cy, radius, angleFor(i));
          const [lx, ly] = polarPoint(cx, cy, radius + 16, angleFor(i));
          return (
            <React.Fragment key={`axis-${i}`}>
              <Line x1={cx} y1={cy} x2={x} y2={y} stroke={colors.border} strokeWidth={1} />
              <SvgText
                x={lx}
                y={ly}
                fontSize={11}
                fill={colors.textMuted}
                textAnchor="middle"
                alignmentBaseline="middle"
              >
                {axis.label}
              </SvgText>
            </React.Fragment>
          );
        })}

        {/* スコアポリゴン */}
        <Polygon
          points={scorePoints}
          fill={colors.accent}
          fillOpacity={0.25}
          stroke={colors.accent}
          strokeWidth={2}
        />

        {/* 各頂点のドット */}
        {axes.map((axis, i) => {
          const ratio = Math.max(0, Math.min(1, axis.value / maxValue));
          const [x, y] = polarPoint(cx, cy, radius * ratio, angleFor(i));
          return <Circle key={`dot-${i}`} cx={x} cy={y} r={3} fill={colors.accent} />;
        })}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", justifyContent: "center" },
});
