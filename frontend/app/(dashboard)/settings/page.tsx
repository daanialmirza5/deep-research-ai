"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import * as React from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentUser } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const APPEARANCE_OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

export default function SettingsPage() {
  const { data: user } = useCurrentUser();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  // See components/theme-toggle.tsx for why this effect is exempted.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  React.useEffect(() => setMounted(true), []);

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Your account details.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  value={user?.full_name ?? ""}
                  disabled
                  readOnly
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={user?.email ?? ""} disabled readOnly />
              </div>
              <p className="text-xs text-muted-foreground">
                Editing profile fields requires a `PATCH /users/me` endpoint,
                not yet built.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="providers">
          <Card>
            <CardHeader>
              <CardTitle>AI Providers</CardTitle>
              <CardDescription>
                Bring your own API keys for OpenAI/Anthropic, or run fully local
                via Ollama.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Provider selection and API key management land alongside the AI
                Agent Framework (Phase 7) — see the dependency-injection section
                in docs/architecture.md for the planned
                `LLMProvider`/`EmbeddingProvider` design.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>
                Choose how DeepResearch AI looks on this device.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                {APPEARANCE_OPTIONS.map(({ value, label, icon: Icon }) => (
                  <Button
                    key={value}
                    variant="outline"
                    className={cn(
                      mounted &&
                        theme === value &&
                        "border-primary text-primary",
                    )}
                    onClick={() => setTheme(value)}
                  >
                    <Icon /> {label}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
