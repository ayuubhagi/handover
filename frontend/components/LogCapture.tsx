"use client";
import { useEffect } from "react";
import { installLogCapture } from "../lib/debuglog";

export function LogCapture() {
  useEffect(installLogCapture, []);
  return null;
}
