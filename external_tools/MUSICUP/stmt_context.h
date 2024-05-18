#ifndef MUSIC_STMT_CONTEXT_H_
#define MUSIC_STMT_CONTEXT_H_ 

#include <vector>
#include <string>
#include <utility>
#include <map>

#include "clang/Frontend/CompilerInstance.h"
#include "clang/AST/ASTConsumer.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/AST/ASTContext.h"

typedef std::vector<std::pair<clang::Stmt*, clang::SourceRange>> StmtScopeRangeList;
typedef std::vector<clang::SourceRange> ScopeRangeList;

class StmtContext
{
public:
	// initialize to 0
  int proteumstyle_stmt_start_line_num_;
  int last_return_statement_line_num_;

	// initialize to false
  bool is_inside_stmtexpr_;
  bool is_inside_array_decl_size_;
  bool is_inside_enumdecl_;
  bool is_assigned_to_special_;
  bool is_lambda_inside_declstmt_;
  bool is_constexpr_;
  bool is_enumclasstype_;
  bool is_casevalue_;

  clang::SourceRange *rhs_of_special_assignment_;
  clang::SourceRange *lhs_of_assignment_range_;
  clang::SourceRange *addressop_range_;
  clang::SourceRange *unary_inc_dec_range_;
  clang::SourceRange *fielddecl_range_;
  clang::SourceRange *currently_parsed_function_range_;
  clang::SourceRange *switchstmt_condition_range_;
  clang::SourceRange *case_value_range_;
  clang::SourceRange *arraysubscript_range_;
  clang::SourceRange *switchcase_range_;
  clang::SourceRange *non_floating_expr_range_;
  clang::SourceRange *typedef_range_;
  clang::SourceRange *Lambda_expr_;
  clang::SourceRange *decl_stmt_;

  std::string currently_parsed_function_name_;

  // list of for/while/do loop that the current statement is in.
  // used for remove stillborn mutants for SBRC.
  StmtScopeRangeList *loop_scope_list_;

public:
	StmtContext(clang::CompilerInstance *CI);

	// getter
	int getProteumStyleLineNum();
	clang::SourceRange* getLhsOfAssignmentRange();

	// setters
	void setProteumStyleLineNum(int num);
	void setIsInStmtExpr(bool value);
	void setIsInArrayDeclSize(bool value);
	void setIsInEnumDecl(bool value);
  void setIsEnumClass(bool value);
  void setIsCaseValue(bool value);
  void setIsInSpecialAssignment(bool value);
  void setIslambdaInDeclstmt(bool value);
  void setIsInConstExpr(bool value);
	void setLhsOfAssignmentRange(clang::SourceRange *range);
  void setRhsOfSpecialAssignmentRange(clang::SourceRange *range);
  void setLambdaExprRange(clang::SourceRange *range);
  void setAddressOpRange(clang::SourceRange *range);
  void setUnaryIncrementDecrementRange(clang::SourceRange *range);
  void setFieldDeclRange(clang::SourceRange *range);
  void setCurrentlyParsedFunctionRange(clang::SourceRange *range);
  void setSwitchStmtConditionRange(clang::SourceRange *range);
  void setCaseValueRange(clang::SourceRange *range);
  void setArraySubscriptRange(clang::SourceRange *range);
  void setSwitchCaseRange(clang::SourceRange *range);
  void setNonFloatingExprRange(clang::SourceRange *range);
  void setTypedefDeclRange(clang::SourceRange *range);
  void setDeclStmtRange(clang::SourceRange *range);
  void setCurrentlyParsedFunctionName(std::string function_name);

	bool IsInStmtExpr();
	bool IsInArrayDeclSize();
	bool IsInEnumDecl();
  bool IsEnumClassType();
  bool IsInLambda();
  bool IsInConstExpr();

	bool IsInLhsOfAssignmentRange(clang::Stmt *s);
  bool IsInRhsOfSpecialAssignmentRange(clang::Stmt *s);
	bool IsInAddressOpRange(clang::Stmt *s);
	bool IsInUnaryIncrementDecrementRange(clang::Stmt *s);
	bool IsInFieldDeclRange(clang::Stmt *s);
	bool IsInCurrentlyParsedFunctionRange(clang::Stmt *s);
	bool IsInSwitchStmtConditionRange(clang::Stmt *s);
  bool IsInCaseValueRange(clang::Expr *s);
	bool IsInArraySubscriptRange(clang::Stmt *s);
	bool IsInSwitchCaseRange(clang::Stmt *s);
	bool IsInNonFloatingExprRange(clang::Stmt *s);
	bool IsInTypedefRange(clang::Stmt *s);
  bool IsInLambdaRange(clang::SourceLocation loc);
  bool IsInDeclStmt(clang::SourceLocation loc);

  bool IsInCurrentlyParsedFunctionRange(clang::SourceLocation loc);
  bool IsInNonFloatingExprRange(clang::SourceLocation loc);
  bool IsInTypedefRange(clang::SourceLocation loc);

  // Check if the given location is inside any loop.
  // Update the loop_scope_list_ at the same time.
  bool IsInLoopRange(clang::SourceLocation loc);

  std::string getContainingFunction(clang::SourceLocation loc, clang::SourceManager& src_mgr);
};

#endif	// MUSIC_STMT_CONTEXT_H_