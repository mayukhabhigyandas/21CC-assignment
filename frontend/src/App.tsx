import { useEffect, useState, type FormEvent } from "react";

type LearnerSkill = { name: string; level: number };
type Profile = { bio: string; skills: LearnerSkill[] };
type OpportunityType = "job" | "course";
type MatchMode = "hybrid" | "rules";
type MissingSkill = { name: string; required: number; learner: number | null };
type Opportunity = {
  id: number;
  title: string;
  type: OpportunityType;
  description: string;
  location_or_mode: string;
};
type Match = {
  opportunity: Opportunity;
  score: number;
  matched_skills: string[];
  missing_skills: MissingSkill[];
  explanation: string;
  signals: {
    rule?: number;
    semantic?: number | null;
    rule_contribution?: number;
    semantic_contribution?: number;
  };
};
type MatchResponse = { items: Match[] };
type AuthResponse = { access_token: string; token_type: string };
type AuthMode = "login" | "signup";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");
const TOKEN_KEY = "skillmatch-access-token";
const emptyProfile: Profile = { bio: "", skills: [] };

class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null) return fallback;

  if ("error" in payload) {
    const error = payload.error;
    if (
      typeof error === "object" &&
      error !== null &&
      "message" in error &&
      typeof error.message === "string"
    ) {
      return error.message;
    }
  }
  if ("detail" in payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  return fallback;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new Error(`Can't reach the API at ${API_BASE_URL}. Is the backend running?`);
  }

  const responseText = await response.text();
  let payload: unknown;
  if (responseText) {
    try {
      payload = JSON.parse(responseText) as unknown;
    } catch {
      payload = responseText;
    }
  }
  if (!response.ok) {
    throw new ApiError(errorMessage(payload, `Request failed (${response.status})`));
  }
  return payload as T;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function App() {
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem(TOKEN_KEY),
  );
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [profileBusy, setProfileBusy] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileMessage, setProfileMessage] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);
  const [matchesBusy, setMatchesBusy] = useState(true);
  const [matchesError, setMatchesError] = useState("");
  const [mode, setMode] = useState<MatchMode>("hybrid");
  const [opportunityType, setOpportunityType] = useState<"all" | OpportunityType>("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!token) {
      setProfileBusy(false);
      return;
    }

    let active = true;
    setProfileBusy(true);
    setProfileError("");
    request<Profile>("/profile", {}, token)
      .then((data) => {
        if (active) setProfile(data);
      })
      .catch((error: unknown) => {
        if (active) setProfileError(getErrorMessage(error));
      })
      .finally(() => {
        if (active) setProfileBusy(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    if (!token) {
      setMatchesBusy(false);
      return;
    }

    let active = true;
    const params = new URLSearchParams({ mode, limit: "10" });
    if (opportunityType !== "all") params.set("type", opportunityType);

    setMatchesBusy(true);
    setMatchesError("");
    request<MatchResponse>(`/matches?${params.toString()}`, {}, token)
      .then((data) => {
        if (active) setMatches(data.items);
      })
      .catch((error: unknown) => {
        if (active) setMatchesError(getErrorMessage(error));
      })
      .finally(() => {
        if (active) setMatchesBusy(false);
      });

    return () => {
      active = false;
    };
  }, [token, mode, opportunityType, refreshKey]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError("");
    try {
      const path = authMode === "login" ? "/auth/login" : "/auth/signup";
      const body =
        authMode === "login"
          ? { email, password }
          : { email, password };
      const result = await request<AuthResponse>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      sessionStorage.setItem(TOKEN_KEY, result.access_token);
      setToken(result.access_token);
    } catch (error) {
      setAuthError(getErrorMessage(error));
    } finally {
      setAuthBusy(false);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileSaving(true);
    setProfileError("");
    setProfileMessage("");
    try {
      const updated = await request<Profile>(
        "/profile",
        {
          method: "PUT",
          body: JSON.stringify({
            bio: profile.bio,
            skills: profile.skills.map((skill) => ({
              name: skill.name.trim(),
              level: skill.level,
            })),
          }),
        },
        token ?? undefined,
      );
      setProfile(updated);
      setProfileMessage("Your profile is saved. Matches have been refreshed.");
      setRefreshKey((current) => current + 1);
    } catch (error) {
      setProfileError(getErrorMessage(error));
    } finally {
      setProfileSaving(false);
    }
  }

  function updateSkill(index: number, patch: Partial<LearnerSkill>) {
    setProfile((current) => ({
      ...current,
      skills: current.skills.map((skill, skillIndex) =>
        skillIndex === index ? { ...skill, ...patch } : skill,
      ),
    }));
    setProfileMessage("");
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setProfile(emptyProfile);
    setMatches([]);
    setProfileError("");
    setMatchesError("");
  }

  if (!token) {
    return (
      <main className="auth-layout">
        <section className="auth-intro">
          <div className="brand">
            <span className="brand-mark">S</span>
            <span>SkillMatch</span>
          </div>
          <div className="intro-copy">
            <p className="eyebrow">A better next step</p>
            <h1>Find the work that fits the skills you’re building.</h1>
            <p>
              Keep your skills in one place and see opportunities ranked with a
              clear explanation of every match.
            </p>
          </div>
          <div className="intro-foot">Personalized opportunities, made clearer.</div>
        </section>

        <section className="auth-panel">
          <form className="auth-card" onSubmit={submitAuth}>
            <p className="eyebrow">{authMode === "login" ? "Welcome back" : "Get started"}</p>
            <h2>{authMode === "login" ? "Sign in to SkillMatch" : "Create your learner account"}</h2>
            <p className="muted">
              {authMode === "login"
                ? "Use your learner account to update your profile and explore matches."
                : "Create an account to save your skills and see personalized matches."}
            </p>

            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              autoComplete="email"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
              type="email"
              value={email}
            />

            <label className="field-label" htmlFor="password">
              Password
            </label>
            <input
              autoComplete={authMode === "login" ? "current-password" : "new-password"}
              id="password"
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />

            {authError && <p className="alert alert-error" role="alert">{authError}</p>}

            <button className="button button-primary auth-submit" disabled={authBusy} type="submit">
              {authBusy
                ? "Please wait..."
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
            <p className="auth-switch">
              {authMode === "login" ? "New to SkillMatch?" : "Already have an account?"}{" "}
              <button
                className="text-button"
                onClick={() => {
                  setAuthMode(authMode === "login" ? "signup" : "login");
                  setAuthError("");
                }}
                type="button"
              >
                {authMode === "login" ? "Create an account" : "Sign in"}
              </button>
            </p>
            <p className="demo-hint">
              Try the seeded learner account: <strong>learner1@example.com</strong>
              <br />
              Password: <strong>learner123</strong>
            </p>
          </form>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a aria-label="SkillMatch home" className="brand" href="/">
          <span className="brand-mark">S</span>
          <span>SkillMatch</span>
        </a>
        <div className="topbar-actions">
          <span className="signed-in"><span className="online-dot" /> Learner workspace</span>
          <button className="button button-quiet" onClick={logout} type="button">
            Sign out
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="page-heading">
          <div>
            <p className="eyebrow">Your opportunity finder</p>
            <h1>Make your next move count.</h1>
            <p className="muted">
              Keep your skills current and discover roles and courses that match.
            </p>
          </div>
          <div className="heading-note">
            <span className="sparkle">✦</span>
            <span>Ranked for you<br /><strong>with reasons, not just results</strong></span>
          </div>
        </section>

        <div className="dashboard-grid">
          <section aria-labelledby="profile-title" className="panel profile-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Your profile</p>
                <h2 id="profile-title">Skills &amp; experience</h2>
              </div>
              <span className="panel-icon" aria-hidden="true">✎</span>
            </div>
            {profileBusy ? (
              <div className="loading-state">Loading your profile...</div>
            ) : (
              <form onSubmit={saveProfile}>
                <label className="field-label" htmlFor="bio">A little about you</label>
                <textarea
                  id="bio"
                  maxLength={500}
                  onChange={(event) => {
                    setProfile((current) => ({ ...current, bio: event.target.value }));
                    setProfileMessage("");
                  }}
                  placeholder="What kind of work are you interested in?"
                  rows={3}
                  value={profile.bio}
                />
                <div className="skills-heading">
                  <span className="field-label">Your skills</span>
                  <span className="muted small-text">Rate each from 1 to 5</span>
                </div>
                <div className="skill-list">
                  {profile.skills.map((skill, index) => (
                    <div className="skill-row" key={`${index}-${skill.name}`}>
                      <input
                        aria-label={`Skill ${index + 1} name`}
                        maxLength={80}
                        onChange={(event) => updateSkill(index, { name: event.target.value })}
                        placeholder="e.g. Python"
                        required
                        value={skill.name}
                      />
                      <select
                        aria-label={`Skill ${index + 1} level`}
                        onChange={(event) => updateSkill(index, { level: Number(event.target.value) })}
                        value={skill.level}
                      >
                        {[1, 2, 3, 4, 5].map((level) => (
                          <option key={level} value={level}>{level} / 5</option>
                        ))}
                      </select>
                      <button
                        aria-label={`Remove ${skill.name || `skill ${index + 1}`}`}
                        className="icon-button"
                        onClick={() => {
                          setProfile((current) => ({
                            ...current,
                            skills: current.skills.filter((_, skillIndex) => skillIndex !== index),
                          }));
                          setProfileMessage("");
                        }}
                        type="button"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  className="button button-add"
                  onClick={() => setProfile((current) => ({
                    ...current,
                    skills: [...current.skills, { name: "", level: 3 }],
                  }))}
                  type="button"
                >
                  <span aria-hidden="true">+</span> Add a skill
                </button>

                {profileError && <p className="alert alert-error" role="alert">{profileError}</p>}
                {profileMessage && <p className="alert alert-success" role="status">{profileMessage}</p>}

                <button
                  className="button button-primary save-button"
                  disabled={profileSaving || profile.skills.some((skill) => !skill.name.trim())}
                  type="submit"
                >
                  {profileSaving ? "Saving profile..." : "Save profile"}
                </button>
              </form>
            )}
          </section>

          <section aria-labelledby="matches-title" className="matches-column">
            <div className="matches-toolbar">
              <div>
                <p className="eyebrow">A shortlist for you</p>
                <h2 id="matches-title">Your matches</h2>
              </div>
              <div className="filters">
                <label>
                  <span className="sr-only">Match ranking</span>
                  <select
                    onChange={(event) => setMode(event.target.value as MatchMode)}
                    value={mode}
                  >
                    <option value="hybrid">Best overall</option>
                    <option value="rules">Skill fit</option>
                  </select>
                </label>
                <label>
                  <span className="sr-only">Opportunity type</span>
                  <select
                    onChange={(event) => setOpportunityType(event.target.value as "all" | OpportunityType)}
                    value={opportunityType}
                  >
                    <option value="all">All types</option>
                    <option value="job">Jobs</option>
                    <option value="course">Courses</option>
                  </select>
                </label>
                <button
                  aria-label="Refresh matches"
                  className="button button-refresh"
                  disabled={matchesBusy}
                  onClick={() => setRefreshKey((current) => current + 1)}
                  type="button"
                >
                  ↻
                </button>
              </div>
            </div>

            {matchesError && <p className="alert alert-error" role="alert">{matchesError}</p>}
            {matchesBusy ? (
              <div className="panel loading-state">Finding your best matches...</div>
            ) : matches.length === 0 ? (
              <div className="panel empty-state">
                <span aria-hidden="true">◎</span>
                <h3>No opportunities found</h3>
                <p>Try another filter or check back when more opportunities are available.</p>
              </div>
            ) : (
              <div className="match-list">
                {matches.map((match, index) => (
                  <article className="match-card" key={match.opportunity.id}>
                    <div className="match-rank">{String(index + 1).padStart(2, "0")}</div>
                    <div className="match-content">
                      <div className="match-title-row">
                        <div>
                          <div className="match-tags">
                            <span className={`type-tag type-${match.opportunity.type}`}>
                              {match.opportunity.type}
                            </span>
                            <span className="location-tag">{match.opportunity.location_or_mode}</span>
                          </div>
                          <h3>{match.opportunity.title}</h3>
                        </div>
                        <div className="score-pill">
                          <strong>{match.score.toFixed(1)}</strong>
                          <span>{mode === "rules" ? "skill fit" : "rank score"}</span>
                        </div>
                      </div>
                      <p className="match-description">{match.opportunity.description}</p>
                      <div className="explanation">
                        <span className="explanation-icon" aria-hidden="true">✦</span>
                        <div><strong>Why it matches</strong><p>{match.explanation}</p></div>
                      </div>
                      <div className="match-details">
                        <div className="detail-group">
                          <span className="detail-label">Matched skills</span>
                          {match.matched_skills.length > 0 ? (
                            <div className="chip-list">
                              {match.matched_skills.map((skill) => (
                                <span className="skill-chip matched-chip" key={skill}>{skill}</span>
                              ))}
                            </div>
                          ) : <span className="detail-muted">No required skills matched yet</span>}
                        </div>
                        {match.missing_skills.length > 0 && (
                          <div className="detail-group">
                            <span className="detail-label">Skills to build</span>
                            <div className="chip-list">
                              {match.missing_skills.map((skill) => (
                                <span className="skill-chip missing-chip" key={skill.name}>
                                  {skill.name} · level {skill.required}
                                  {skill.learner === null ? "" : ` (you: ${skill.learner})`}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      {match.signals.rule_contribution !== undefined && (
                        <div className="signal-row">
                          <span>Ranking signals</span>
                          <span>Skill fit {match.signals.rule_contribution.toFixed(1)}</span>
                          <span>Semantic {match.signals.semantic_contribution?.toFixed(1) ?? "0.0"}</span>
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
        <footer className="page-footer">SkillMatch · Your skills, connected to what’s next.</footer>
      </main>
    </div>
  );
}

export default App;
