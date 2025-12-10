import { ref, onMounted, type Ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

export function useSearch() {
  const router = useRouter();

  const searchKeyword: Ref<string> = ref("");
  const showSearchPanel: Ref<boolean> = ref(false);
  const searchHistory: Ref<string[]> = ref([]);
  const trendingSearches: Ref<string[]> = ref([
    "AI 技术解析",
    "Vue 3 新特性",
    "前端性能优化",
    "TypeScript 入门",
    "React vs Vue",
    "Web3.0 趋势",
    "微前端架构",
    "Vite 构建工具",
    "CSS 动画技巧",
    "JavaScript 设计模式",
  ]);

  const persistHistory = () => {
    localStorage.setItem("searchHistory", JSON.stringify(searchHistory.value));
  };

  const loadHistory = () => {
    const saved = localStorage.getItem("searchHistory");
    if (saved) {
      try {
        searchHistory.value = JSON.parse(saved) as string[];
      } catch (error) {
        console.error("加载搜索历史失败:", error);
      }
    }
  };

  const handleSearch = () => {
    if (!searchKeyword.value.trim()) {
      ElMessage.warning("请输入搜索关键词");
      return;
    }

    if (!searchHistory.value.includes(searchKeyword.value)) {
      searchHistory.value.unshift(searchKeyword.value);
      if (searchHistory.value.length > 10) {
        searchHistory.value.pop();
      }
      persistHistory();
    }

    router.push({
      path: "/search",
      query: {
        keyword: searchKeyword.value,
      },
    });

    showSearchPanel.value = false;
  };

  const handleFocus = () => {
    showSearchPanel.value = true;
  };

  const handleBlur = () => {
    setTimeout(() => {
      showSearchPanel.value = false;
    }, 200);
  };

  const selectHistory = (keyword: string) => {
    searchKeyword.value = keyword;
    handleSearch();
  };

  const selectTrending = (keyword: string) => {
    searchKeyword.value = keyword;
    handleSearch();
  };

  const clearHistory = () => {
    searchHistory.value = [];
    localStorage.removeItem("searchHistory");
  };

  onMounted(() => {
    loadHistory();
  });

  return {
    searchKeyword,
    searchHistory,
    trendingSearches,
    showSearchPanel,
    handleSearch,
    handleFocus,
    handleBlur,
    selectHistory,
    selectTrending,
    clearHistory,
  };
}

