/**
 * 基本画面の統合テスト。
 * fetch をモックしてバックエンドなしで検証する。
 */

import { fireEvent, render, waitFor } from "@testing-library/react-native";
import React from "react";

import App from "../../../App";
import * as api from "../../utils/api";

const ME = {
  id: "u-1",
  email: "athlete@example.com",
  role: "athlete",
  is_active: true,
};

function mockFetch(routes: Record<string, { status: number; body: unknown }>) {
  global.fetch = jest.fn(async (url: string) => {
    const path = String(url).replace(/^https?:\/\/[^/]+/, "");
    const match = Object.entries(routes).find(([p]) => path.startsWith(p));
    const route = match?.[1] ?? { status: 404, body: { detail: "not found" } };
    return {
      ok: route.status < 400,
      status: route.status,
      json: async () => route.body,
    };
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  api.setToken(null);
  jest.clearAllMocks();
});

describe("ログイン画面", () => {
  it("初期表示ではログイン画面が出る", () => {
    const { getByTestId } = render(<App />);
    expect(getByTestId("login-email-input")).toBeTruthy();
  });

  it("メールアドレス未入力ではログインボタンが無効", () => {
    const { getByTestId } = render(<App />);
    expect(getByTestId("login-submit").props.accessibilityState.disabled).toBe(true);
  });

  it("ログイン成功でホーム画面に遷移する", async () => {
    mockFetch({
      "/api/auth/login": {
        status: 200,
        body: { access_token: "tok", token_type: "bearer" },
      },
      "/api/auth/me": { status: 200, body: ME },
      "/api/videos": { status: 200, body: [] },
    });

    const { getByTestId, getByText } = render(<App />);
    fireEvent.changeText(getByTestId("login-email-input"), ME.email);
    fireEvent.press(getByTestId("login-submit"));

    await waitFor(() => expect(getByText(`${ME.email} でログイン中`)).toBeTruthy());
  });

  it("ログイン失敗でエラーメッセージが出る", async () => {
    mockFetch({
      "/api/auth/login": {
        status: 401,
        body: { detail: "メールアドレスまたはパスワードが正しくありません" },
      },
    });

    const { getByTestId } = render(<App />);
    fireEvent.changeText(getByTestId("login-email-input"), "x@example.com");
    fireEvent.press(getByTestId("login-submit"));

    await waitFor(() => expect(getByTestId("login-error")).toBeTruthy());
  });
});

describe("ログイン後のタブ操作", () => {
  async function loginToHome() {
    mockFetch({
      "/api/auth/login": {
        status: 200,
        body: { access_token: "tok", token_type: "bearer" },
      },
      "/api/auth/me": { status: 200, body: ME },
      "/api/videos/upload-url": {
        status: 201,
        body: {
          video_id: "12345678-aaaa-bbbb-cccc-000000000000",
          presigned_url: "https://s3.example.com/put",
          s3_key: "videos/p/x.mp4",
        },
      },
      "/api/videos/v-1/analysis": {
        status: 200,
        body: {
          id: "a-1",
          video_id: "v-1",
          sprint_score: 72.5,
          ball_control_score: 65,
          positioning_score: 80,
          body_usage_score: 58,
          total_score: 69.4,
          confidence: 0.1,
          feedback: "【開発中】このスコアはプレースホルダーです。",
          analyzed_at: "2026-07-02T00:00:00Z",
          is_reference_score: true,
        },
      },
      "/api/videos": {
        status: 200,
        body: [
          {
            id: "v-1",
            athlete_id: "p-1",
            s3_key: "videos/p-1/practice.mp4",
            status: "completed",
            duration_sec: 90,
          },
        ],
      },
    });

    const utils = render(<App />);
    fireEvent.changeText(utils.getByTestId("login-email-input"), ME.email);
    fireEvent.press(utils.getByTestId("login-submit"));
    await waitFor(() => expect(utils.getByText(`${ME.email} でログイン中`)).toBeTruthy());
    return utils;
  }

  it("ホームに動画一覧が表示される", async () => {
    const { getByTestId } = await loginToHome();
    await waitFor(() => expect(getByTestId("video-v-1")).toBeTruthy());
  });

  it("アップロードタブで Presigned URL を取得できる", async () => {
    const { getByTestId } = await loginToHome();
    fireEvent.press(getByTestId("tab-upload"));
    fireEvent.press(getByTestId("upload-request-button"));
    await waitFor(() => expect(getByTestId("upload-ready")).toBeTruthy());
  });

  it("プロフィールタブでログアウトするとログイン画面に戻る", async () => {
    const { getByTestId } = await loginToHome();
    fireEvent.press(getByTestId("tab-profile"));
    fireEvent.press(getByTestId("logout-button"));
    await waitFor(() => expect(getByTestId("login-email-input")).toBeTruthy());
  });

  it("完了動画をタップするとスコア画面が開きレーダーチャートが表示される", async () => {
    const { getByTestId } = await loginToHome();
    await waitFor(() => expect(getByTestId("video-v-1")).toBeTruthy());

    fireEvent.press(getByTestId("video-v-1"));

    await waitFor(() => expect(getByTestId("radar-chart")).toBeTruthy());
    expect(getByTestId("score-total")).toBeTruthy();
    expect(getByTestId("score-disclaimer")).toBeTruthy();
  });

  it("スコア画面から戻るとホームに戻る", async () => {
    const { getByTestId } = await loginToHome();
    await waitFor(() => expect(getByTestId("video-v-1")).toBeTruthy());
    fireEvent.press(getByTestId("video-v-1"));
    await waitFor(() => expect(getByTestId("score-back")).toBeTruthy());

    fireEvent.press(getByTestId("score-back"));
    await waitFor(() => expect(getByTestId("video-v-1")).toBeTruthy());
  });
});
