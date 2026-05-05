import { expect, type APIRequestContext, type Page } from '@playwright/test';

export const E2E_API_URL = process.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
export const E2E_PROFILE_NAME = process.env.HC_E2E_PROFILE_NAME || 'Playwright E2E Profile';
export const E2E_PROFILE_PASSWORD = process.env.HC_E2E_PROFILE_PASSWORD || 'SecurePass123';

interface ProfileListItem {
  id: string;
  display_name: string;
}

interface TokenResponse {
  access_token: string;
  expires_in: number;
  profile_id: string;
  profile_name: string;
}

export async function ensureE2EProfile(request: APIRequestContext): Promise<TokenResponse> {
  const profilesResponse = await request.get(`${E2E_API_URL}/profiles/`);
  expect(profilesResponse.ok(), await profilesResponse.text()).toBeTruthy();

  const profiles = (await profilesResponse.json()) as ProfileListItem[];
  const existing = profiles.find((profile) => profile.display_name === E2E_PROFILE_NAME);

  if (existing) {
    const loginResponse = await request.post(`${E2E_API_URL}/profiles/login`, {
      data: {
        profile_id: existing.id,
        password: E2E_PROFILE_PASSWORD,
      },
    });
    expect(loginResponse.ok(), await loginResponse.text()).toBeTruthy();
    return loginResponse.json() as Promise<TokenResponse>;
  }

  const createResponse = await request.post(`${E2E_API_URL}/profiles/`, {
    data: {
      display_name: E2E_PROFILE_NAME,
      password: E2E_PROFILE_PASSWORD,
    },
  });
  expect(createResponse.ok(), await createResponse.text()).toBeTruthy();
  return createResponse.json() as Promise<TokenResponse>;
}

export async function resetE2EProfile(
  request: APIRequestContext,
  token: string
): Promise<void> {
  const resetResponse = await request.post(`${E2E_API_URL}/profiles/test/reset`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const resetBody = await resetResponse.text();
  if (!resetResponse.ok()) {
    throw new Error(`Reset failed with ${resetResponse.status()}: ${resetBody}`);
  }
}

export async function seedAuthenticatedSession(
  page: Page,
  request: APIRequestContext,
  profileName = E2E_PROFILE_NAME
): Promise<TokenResponse> {
  const tokenResponse = await ensureE2EProfile(request);
  await page.addInitScript(
    ({ auth, profileName }) => {
      localStorage.clear();
      localStorage.setItem(
        'healthcentral-auth',
        JSON.stringify({
          state: {
            token: auth.access_token,
            profileId: auth.profile_id,
            profileName,
            expiresAt: Date.now() + auth.expires_in * 1000,
            isAuthenticated: true,
          },
          version: 0,
        })
      );
    },
    { auth: tokenResponse, profileName }
  );
  return tokenResponse;
}

export async function openAuthenticatedPage(
  page: Page,
  request: APIRequestContext,
  path = '/inbox'
): Promise<TokenResponse> {
  const tokenResponse = await seedAuthenticatedSession(page, request);
  await page.goto(path);
  return tokenResponse;
}
