// src/services/cart.service.ts
// LocalStorage-backed cart service scoped to logged-in user

import type { Product } from "../types";

export interface CartItem {
  product_id: string;
  name: string;
  brand?: string;
  price: number;
  quantity: number;
  image_url?: string;
  stock: number;
}

const getCartKey = (userId: string) => `cf_cart_${userId}`;

export const cartService = {
  getCart(userId?: string): CartItem[] {
    if (!userId) return [];
    try {
      const raw = localStorage.getItem(getCartKey(userId));
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  saveCart(userId: string, items: CartItem[]): void {
    if (!userId) return;
    try {
      localStorage.setItem(getCartKey(userId), JSON.stringify(items));
      // Dispatch custom storage event for header badge sync across tabs/components
      window.dispatchEvent(new Event("cart_updated"));
    } catch {}
  },

  addToCart(userId: string, product: Product, quantity: number): CartItem[] {
    const cart = cartService.getCart(userId);
    const existingIdx = cart.findIndex((i) => i.product_id === product.id);

    const primaryImage =
      product.images?.find((img) => img.is_primary)?.image_url ??
      product.images?.[0]?.image_url ??
      product.image_url;

    const availableStock = product.stock ?? 99;

    if (existingIdx >= 0) {
      const newQty = Math.min(
        cart[existingIdx].quantity + quantity,
        availableStock
      );
      cart[existingIdx].quantity = newQty;
    } else {
      cart.push({
        product_id: product.id,
        name: product.name,
        brand: product.brand,
        price: Number(product.price),
        quantity: Math.min(quantity, availableStock),
        image_url: primaryImage,
        stock: availableStock,
      });
    }

    cartService.saveCart(userId, cart);
    return cart;
  },

  updateQuantity(userId: string, productId: string, quantity: number): CartItem[] {
    let cart = cartService.getCart(userId);
    if (quantity <= 0) {
      cart = cart.filter((i) => i.product_id !== productId);
    } else {
      const item = cart.find((i) => i.product_id === productId);
      if (item) {
        item.quantity = Math.min(quantity, item.stock);
      }
    }
    cartService.saveCart(userId, cart);
    return cart;
  },

  removeFromCart(userId: string, productId: string): CartItem[] {
    const cart = cartService.getCart(userId).filter((i) => i.product_id !== productId);
    cartService.saveCart(userId, cart);
    return cart;
  },

  clearCart(userId: string): void {
    if (!userId) return;
    try {
      localStorage.removeItem(getCartKey(userId));
      window.dispatchEvent(new Event("cart_updated"));
    } catch {}
  },

  getCartCount(userId?: string): number {
    const cart = cartService.getCart(userId);
    return cart.reduce((acc, item) => acc + item.quantity, 0);
  },

  getSubtotal(userId?: string): number {
    const cart = cartService.getCart(userId);
    return cart.reduce((acc, item) => acc + item.price * item.quantity, 0);
  },
};

export default cartService;
