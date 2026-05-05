import Button from "../common/Button.jsx";
import Input from "../common/Input.jsx";

const orderingOptions = [
  { value: "start_datetime", label: "Start date ascending" },
  { value: "-start_datetime", label: "Start date descending" },
  { value: "title", label: "Title A-Z" },
  { value: "-created_at", label: "Newest first" },
];

export default function EventFilters({
  filters,
  categories = [],
  onChange,
  onReset,
}) {
  function handleChange(event) {
    onChange({
      ...filters,
      [event.target.name]: event.target.value,
      page: 1,
    });
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Input
          label="Search"
          name="search"
          value={filters.search}
          onChange={handleChange}
          placeholder="Event title, topic, location"
        />
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Category
          </span>
          <select
            name="category"
            value={filters.category}
            onChange={handleChange}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Location"
          name="location"
          value={filters.location}
          onChange={handleChange}
          placeholder="City or venue"
        />
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Ordering
          </span>
          <select
            name="ordering"
            value={filters.ordering}
            onChange={handleChange}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            {orderingOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-4 flex justify-end">
        <Button variant="ghost" onClick={onReset}>
          Reset filters
        </Button>
      </div>
    </section>
  );
}
