#include "AST/CompoundStatement.hpp"
#include "AST/for.hpp"
#include "AST/function.hpp"
#include "AST/program.hpp"
#include "codegen/CodeGenerator.hpp"
#include "sema/SemanticAnalyzer.hpp"
#include "sema/SymbolTable.hpp"
#include "visitor/AstNodeInclude.hpp"

#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>

CodeGenerator::CodeGenerator(const std::string &source_file_name,
                             const std::string &save_path,
                             std::unordered_map<SemanticAnalyzer::AstNodeAddr,
                                                      SymbolManager::Table>
                                 &&p_symbol_table_of_scoping_nodes)
    : m_symbol_manager(false /* no dump */),
      m_source_file_path(source_file_name),
      m_symbol_table_of_scoping_nodes(std::move(p_symbol_table_of_scoping_nodes)) {
    // FIXME: assume that the source file is always xxxx.p
    const auto &real_path =
        save_path.empty() ? std::string{"."} : save_path;
    auto slash_pos = source_file_name.rfind('/');
    auto dot_pos = source_file_name.rfind('.');

    if (slash_pos != std::string::npos) {
        ++slash_pos;
    } else {
        slash_pos = 0;
    }
    auto output_file_path{
        real_path + "/" +
        source_file_name.substr(slash_pos, dot_pos - slash_pos) + ".S"};
    m_output_file.reset(fopen(output_file_path.c_str(), "w"));
    assert(m_output_file.get() && "Failed to open output file");
}

static void dumpInstructions(FILE *p_out_file, const char *format, ...) {
    va_list args;
    va_start(args, format);
    vfprintf(p_out_file, format, args);
    va_end(args);
}

// --------------------------------------------------------------------------
//  Helper utilities
// --------------------------------------------------------------------------

namespace {
constexpr int kLocalVariableStartOffset = -12; // see README examples
}

// Keep track of the current stack offset for local variables within a function
static int current_local_offset = kLocalVariableStartOffset;
static std::vector<int> offset_stack;

static bool in_text_section = true;

static void switchToTextSection(FILE *out) {
    if (!in_text_section) {
        dumpInstructions(out, ".section    .text\n    .align 2\n");
        in_text_section = true;
    }
}

static void switchToRodataSection(FILE *out) {
    if (in_text_section) {
        dumpInstructions(out, ".section    .rodata\n    .align 2\n");
        in_text_section = false;
    }
}

void CodeGenerator::visit(ProgramNode &p_program) {
    // Generate RISC-V instructions for program header
    // clang-format off
    constexpr const char *const riscv_assembly_file_prologue =
        "    .file \"%s\"\n"
        "    .option nopic\n"
        ".section    .text\n"
        "    .align 2\n";
    // clang-format on
    dumpInstructions(m_output_file.get(), riscv_assembly_file_prologue,
                     m_source_file_path.c_str());

    // Reconstruct the scope for looking up the symbol entry.
    // Hint: Use m_symbol_manager->lookup(symbol_name) to get the symbol entry.
    m_symbol_manager.pushScope(
        std::move(m_symbol_table_of_scoping_nodes.at(&p_program)));

    auto visit_ast_node = [&](auto &ast_node) { ast_node->accept(*this); };
    for_each(p_program.getDeclNodes().begin(), p_program.getDeclNodes().end(),
             visit_ast_node);
    for_each(p_program.getFuncNodes().begin(), p_program.getFuncNodes().end(),
             visit_ast_node);

    // switch back to text section for main function
    switchToTextSection(m_output_file.get());
    dumpInstructions(m_output_file.get(), "    .globl main\n    .type main, @function\nmain:\n");
    dumpInstructions(m_output_file.get(),
                     "    addi sp, sp, -128\n    sw ra, 124(sp)\n    sw s0, 120(sp)\n    addi s0, sp, 128\n");

    current_local_offset = kLocalVariableStartOffset;
    offset_stack.clear();
    offset_stack.push_back(current_local_offset);

    const_cast<CompoundStatementNode &>(p_program.getBody()).accept(*this);

    dumpInstructions(m_output_file.get(),
                     "    lw ra, 124(sp)\n    lw s0, 120(sp)\n    addi sp, sp, 128\n    jr ra\n    .size main, .-main\n");

    m_symbol_manager.popScope();
}

void CodeGenerator::visit(DeclNode &p_decl) {
    for (auto &var : p_decl.getVariables()) {
        var->accept(*this);
    }
}

void CodeGenerator::visit(VariableNode &p_variable) {
    const auto *entry = m_symbol_manager.lookup(p_variable.getName());
    if (!entry) {
        return;
    }

    if (entry->getLevel() == 0) {
        if (entry->getKind() == SymbolEntry::KindEnum::kVariableKind) {
            dumpInstructions(m_output_file.get(), "    .comm %s, 4, 4\n",
                             entry->getNameCString());
        } else if (entry->getKind() == SymbolEntry::KindEnum::kConstantKind) {
            switchToRodataSection(m_output_file.get());
            dumpInstructions(m_output_file.get(),
                             "    .globl %s\n    .type %s, @object\n%s:\n",
                             entry->getNameCString(), entry->getNameCString(),
                             entry->getNameCString());
            auto value = entry->getAttribute().constant()->integer();
            dumpInstructions(m_output_file.get(), "    .word %ld\n",
                             static_cast<long>(value));
        }
    } else {
        int offset = current_local_offset;
        current_local_offset -= 4;
        offset_stack.back() = current_local_offset;
        m_local_var_offset[entry] = offset;
        if (entry->getKind() == SymbolEntry::KindEnum::kConstantKind) {
            auto value = entry->getAttribute().constant()->integer();
            dumpInstructions(m_output_file.get(),
                             "    li t0, %ld\n    sw t0, %d(s0)\n",
                             static_cast<long>(value), offset);
        }
    }
}

void CodeGenerator::visit(ConstantValueNode &p_constant_value) {
    auto value = p_constant_value.getConstantPtr()->integer();
    dumpInstructions(m_output_file.get(),
                     "    li t0, %ld\n    addi sp, sp, -4\n    sw t0, 0(sp)\n",
                     static_cast<long>(value));
}

void CodeGenerator::visit(FunctionNode &p_function) {
    // Reconstruct the scope for looking up the symbol entry.
    m_symbol_manager.pushScope(
        std::move(m_symbol_table_of_scoping_nodes.at(&p_function)));

    p_function.visitChildNodes(*this);

    // Remove the entries in the hash table
    m_symbol_manager.popScope();
}

void CodeGenerator::visit(CompoundStatementNode &p_compound_statement) {
    // Reconstruct the scope for looking up the symbol entry.
    m_symbol_manager.pushScope(
        std::move(m_symbol_table_of_scoping_nodes.at(&p_compound_statement)));

    offset_stack.push_back(current_local_offset);

    p_compound_statement.visitChildNodes(*this);

    current_local_offset = offset_stack.back();
    offset_stack.pop_back();

    m_symbol_manager.popScope();
}

void CodeGenerator::visit(PrintNode &p_print) {
    const_cast<ExpressionNode &>(p_print.getTarget()).accept(*this);
    dumpInstructions(m_output_file.get(),
                     "    lw a0, 0(sp)\n    addi sp, sp, 4\n    jal ra, printInt\n");
}

void CodeGenerator::visit(BinaryOperatorNode &p_bin_op) {}

void CodeGenerator::visit(UnaryOperatorNode &p_un_op) {}

void CodeGenerator::visit(FunctionInvocationNode &p_func_invocation) {}

void CodeGenerator::visit(VariableReferenceNode &p_variable_ref) {
    const auto *entry = m_symbol_manager.lookup(p_variable_ref.getName());
    if (!entry) {
        return;
    }

    if (entry->getLevel() == 0) {
        // global variable or constant stored in memory/rodata
        dumpInstructions(m_output_file.get(), "    la t0, %s\n", entry->getNameCString());
        dumpInstructions(m_output_file.get(), "    lw t1, 0(t0)\n    mv t0, t1\n");
    } else {
        auto it = m_local_var_offset.find(entry);
        int offset = (it != m_local_var_offset.end()) ? it->second : 0;
        dumpInstructions(m_output_file.get(), "    lw t0, %d(s0)\n", offset);
    }
    dumpInstructions(m_output_file.get(), "    addi sp, sp, -4\n    sw t0, 0(sp)\n");
}

void CodeGenerator::visit(AssignmentNode &p_assignment) {
    const auto &lvalue = p_assignment.getLvalue();
    const auto *entry = m_symbol_manager.lookup(lvalue.getName());
    if (!entry) {
        return;
    }

    if (entry->getLevel() == 0) {
        dumpInstructions(m_output_file.get(), "    la t0, %s\n", entry->getNameCString());
    } else {
        auto it = m_local_var_offset.find(entry);
        int offset = (it != m_local_var_offset.end()) ? it->second : 0;
        dumpInstructions(m_output_file.get(), "    addi t0, s0, %d\n", offset);
    }
    dumpInstructions(m_output_file.get(), "    addi sp, sp, -4\n    sw t0, 0(sp)\n");

    const_cast<ExpressionNode &>(p_assignment.getExpr()).accept(*this);

    dumpInstructions(m_output_file.get(),
                     "    lw t0, 0(sp)\n    addi sp, sp, 4\n    lw t1, 0(sp)\n    addi sp, sp, 4\n    sw t0, 0(t1)\n");
}

void CodeGenerator::visit(ReadNode &p_read) {}

void CodeGenerator::visit(IfNode &p_if) {}

void CodeGenerator::visit(WhileNode &p_while) {}

void CodeGenerator::visit(ForNode &p_for) {
    // Reconstruct the scope for looking up the symbol entry.
    m_symbol_manager.pushScope(
        std::move(m_symbol_table_of_scoping_nodes.at(&p_for)));

    p_for.visitChildNodes(*this);

    // Remove the entries in the hash table
    m_symbol_manager.popScope();
}

void CodeGenerator::visit(ReturnNode &p_return) {}
