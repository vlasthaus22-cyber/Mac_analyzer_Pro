import { database } from "./database.js";

/** Enriches physical address, vendor and known model without blocking the UI. */
export async function enrichDeviceData(devices, options = {}) {
  try {
    return await database().enrichData(devices, options);
  } catch (error) {
    throw new Error(`Не удалось выполнить обогащение: ${error?.message || error}`);
  }
}

export const resolvePhysicalAddress = (ip) => database().resolvePhysicalAddress(ip);
