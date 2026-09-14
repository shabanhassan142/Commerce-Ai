// src/pages/Register.tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { stagger, staggerItem } from "../animations/variants";
import AuthLayout from "../layouts/AuthLayout";
import useAuth from "../hooks/useAuth";

const registerSchema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain an uppercase letter")
    .regex(/[0-9]/, "Must contain a number"),
  role: z.enum(["customer", "support", "admin"]),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function Register() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerUser(data);
      toast.success("Account created! Welcome to CommerceFlow AI 🎉");
      navigate("/dashboard");
    } catch (err: any) {
      console.error("Register onSubmit error:", err);
      const msg =
        err?.response?.data?.message ??
        err?.response?.data?.detail ??
        err?.message ??
        "Registration failed";
      toast.error(msg);
    }
  };

  return (
    <AuthLayout
      title="Create account"
      subtitle="Join CommerceFlow AI — your smart support platform"
    >
      <motion.form
        variants={stagger}
        initial="hidden"
        animate="visible"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
      >
        {/* Full Name */}
        <motion.div variants={staggerItem}>
          <label className="label" htmlFor="reg-name">Full name</label>
          <input
            id="reg-name"
            type="text"
            placeholder="Alice Johnson"
            className={`input-field ${errors.full_name ? "border-red-500/60" : ""}`}
            {...register("full_name")}
          />
          {errors.full_name && (
            <p className="text-red-400 text-xs mt-1">{errors.full_name.message}</p>
          )}
        </motion.div>

        {/* Email */}
        <motion.div variants={staggerItem}>
          <label className="label" htmlFor="reg-email">Email address</label>
          <input
            id="reg-email"
            type="email"
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
          <label className="label" htmlFor="reg-password">Password</label>
          <div className="relative">
            <input
              id="reg-password"
              type={showPassword ? "text" : "password"}
              placeholder="Min 8 chars, 1 uppercase, 1 number"
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

        {/* Role */}
        <motion.div variants={staggerItem}>
          <label className="label" htmlFor="reg-role">Account type</label>
          <select
            id="reg-role"
            className="input-field"
            {...register("role")}
          >
            <option value="customer">Customer</option>
            <option value="support">Support Agent</option>
            <option value="admin">Administrator</option>
          </select>
        </motion.div>

        {/* Submit */}
        <motion.div variants={staggerItem} className="pt-1">
          <button
            id="reg-submit"
            type="submit"
            disabled={isSubmitting}
            className="w-full btn-primary flex items-center justify-center gap-2 py-3"
          >
            {isSubmitting ? (
              <><Loader2 size={16} className="animate-spin" /> Creating account...</>
            ) : (
              "Create account"
            )}
          </button>
        </motion.div>

        <motion.p variants={staggerItem} className="text-center text-sm text-[#8888aa]">
          Already have an account?{" "}
          <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
            Sign in
          </Link>
        </motion.p>
      </motion.form>
    </AuthLayout>
  );
}
