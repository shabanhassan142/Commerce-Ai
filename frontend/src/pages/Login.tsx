// src/pages/Login.tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { staggerItem, stagger } from "../animations/variants";
import AuthLayout from "../layouts/AuthLayout";
import useAuth from "../hooks/useAuth";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err: any) {
      console.error("Login onSubmit error:", err);
      const msg =
        err?.response?.data?.message ??
        err?.response?.data?.detail ??
        err?.message ??
        "Invalid credentials";
      toast.error(msg);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your CommerceFlow AI account"
    >
      <motion.form
        variants={stagger}
        initial="hidden"
        animate="visible"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5"
      >
        {/* Email */}
        <motion.div variants={staggerItem}>
          <label className="label" htmlFor="login-email">Email address</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="alice@example.com"
            className={`input-field ${errors.email ? "border-red-500/60" : ""}`}
            {...register("email")}
          />
          {errors.email && (
            <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>
          )}
        </motion.div>

        {/* Password */}
        <motion.div variants={staggerItem}>
          <label className="label" htmlFor="login-password">Password</label>
          <div className="relative">
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="••••••••"
              className={`input-field pr-11 ${errors.password ? "border-red-500/60" : ""}`}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8888aa] hover:text-white transition-colors"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {errors.password && (
            <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
          )}
        </motion.div>

        {/* Submit */}
        <motion.div variants={staggerItem}>
          <button
            id="login-submit"
            type="submit"
            disabled={isSubmitting}
            className="w-full btn-primary flex items-center justify-center gap-2 py-3"
          >
            {isSubmitting ? (
              <><Loader2 size={16} className="animate-spin" /> Signing in...</>
            ) : (
              "Sign in"
            )}
          </button>
        </motion.div>

        {/* Register link */}
        <motion.p variants={staggerItem} className="text-center text-sm text-[#8888aa]">
          Don't have an account?{" "}
          <Link to="/register" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
            Create one
          </Link>
        </motion.p>
      </motion.form>
    </AuthLayout>
  );
}
