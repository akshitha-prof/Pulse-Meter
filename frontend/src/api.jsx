import axios from "axios";
export const api = axios.create({ baseURL: "" });
export const fmt = (n) => new Intl.NumberFormat("en-US").format(Math.round(n || 0));
export const fmtMoney = (n) => "$" + new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n || 0);
