function joinClasses(...classes) {
  return classes.filter(Boolean).join(" ");
}

export default function Input({
  label,
  id,
  error,
  className = "",
  ...props
}) {
  const inputId = id || props.name;

  return (
    <label className="block">
      {label ? (
        <span className="mb-1.5 block text-sm font-medium text-slate-700">
          {label}
        </span>
      ) : null}
      <input
        id={inputId}
        className={joinClasses(
          "h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm",
          "placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200",
          error ? "border-red-400 focus:border-red-500 focus:ring-red-100" : "",
          className,
        )}
        {...props}
      />
      {error ? <span className="mt-1 block text-sm text-red-600">{error}</span> : null}
    </label>
  );
}
