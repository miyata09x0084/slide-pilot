/**
 * dashboardLoader - DashboardPageのReact Router Loader
 * ページ表示前にスライド履歴を取得
 */

export async function dashboardLoader() {
  const savedUser = localStorage.getItem("user");
  if (!savedUser) return { slides: [] };

  try {
    const user = JSON.parse(savedUser);
    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8001/api";
    const response = await fetch(
      `${apiUrl}/slides?user_id=${encodeURIComponent(user.email)}&limit=20`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch slides: ${response.statusText}`);
    }

    const data = await response.json();
    return { slides: data.slides || [] };
  } catch (err) {
    console.error("Failed to fetch slides:", err);
    return { slides: [] };
  }
}
